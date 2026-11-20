import Foundation
import SwiftSoup

struct LookupFailure: LocalizedError {
    let message: String
    var errorDescription: String? { message }
}

struct Vehicle: Sendable {
    let plate: String
    let fields: [String: String]
    let retrievedAt: Date
    var sourceURL: URL { URL(string: "https://www.carinfo.app/rc-details/\(plate)")! }
    static let labels = ["Make & Model", "Owner Name", "Fuel Type", "Vehicle Class",
                         "Registration Date", "RC Status", "Insurance Validity", "PUC Validity"]
}

enum VehicleParser {
    static func matches(_ text: String, _ pattern: String) -> Bool {
        text.range(of: pattern, options: .regularExpression) != nil
    }

    static func normalize(_ input: String) throws -> String {
        let plate = input.replacingOccurrences(of: "[\\s-]", with: "", options: .regularExpression).uppercased()
        guard matches(plate, "^(?:[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{1,4}|[0-9]{2}BH[0-9]{4}[A-Z]{1,2})$") else {
            throw LookupFailure(message: "Enter a valid Indian registration number, such as MH12XQ4561.")
        }
        return plate
    }

    static func maskedName(_ text: String) -> String? {
        guard !text.isEmpty, text.count <= 100,
              matches(text, "^[A-Za-z*•. -]+$"),
              text.split(separator: " ").allSatisfy({ $0.contains("*") || $0.contains("•") }) else { return nil }
        return text
    }

    static func parse(_ html: String, plate input: String) throws -> Vehicle {
        let plate = try normalize(input)
        let document = try SwiftSoup.parse(html)
        var tokens = [String]()
        // Walk visible text in document order. Never inspect script/hydration data.
        var pending: [Node] = [document]
        while let node = pending.popLast() {
            if let element = node as? Element {
                let style = try element.attr("style").lowercased()
                let ariaHidden = try element.attr("aria-hidden")
                if ["script", "style", "noscript", "template"].contains(element.tagName().lowercased()) ||
                    element.hasAttr("hidden") || ariaHidden == "true" ||
                    matches(style, "display\\s*:\\s*none|visibility\\s*:\\s*hidden") { continue }
            }
            if let text = node as? TextNode {
                let value = text.getWholeText().split(whereSeparator: { $0.isWhitespace }).joined(separator: " ")
                if !value.isEmpty { tokens.append(value) }
            }
            pending.append(contentsOf: node.getChildNodes().reversed())
        }
        let combined = tokens.joined(separator: " ")
        if matches(combined.lowercased(), "verify (?:that )?you are human|access denied|complete the captcha|just a moment") {
            throw LookupFailure(message: "CarInfo requires verification. You can open the source in Safari.")
        }
        guard tokens.contains(where: { (try? normalize($0)) == plate }) else {
            throw LookupFailure(message: "No matching vehicle was found in the public page. It may require login or browser rendering.")
        }
        func labelKey(_ value: String) -> String { value.trimmingCharacters(in: CharacterSet(charactersIn: ":")).lowercased() }
        let labels = Dictionary(uniqueKeysWithValues: Vehicle.labels.map { (labelKey($0), $0) })
        var fields = [String: String]()
        for (labelToken, value) in zip(tokens, tokens.dropFirst()) {
            guard let label = labels[labelKey(labelToken)], labels[labelKey(value)] == nil, value.count <= 160 else { continue }
            if label == "Owner Name" { fields[label] = maskedName(value) }
            else { fields[label] = value }
        }
        let pattern = "Insurance\\s+(?:Expiring|Expired|Expires)\\s+on\\s+(\\d{1,2}[-/][A-Za-z0-9]{2,9}[-/]\\d{4})"
        let regex = try NSRegularExpression(pattern: pattern, options: .caseInsensitive)
        if let match = regex.firstMatch(in: combined, range: NSRange(combined.startIndex..., in: combined)),
           let range = Range(match.range(at: 1), in: combined) { fields["Insurance Validity"] = String(combined[range]) }
        guard fields["Make & Model"] != nil else {
            throw LookupFailure(message: "The page did not contain recognizable vehicle details.")
        }
        return Vehicle(plate: plate, fields: fields, retrievedAt: Date())
    }
}

final class NoRedirects: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    func urlSession(_ session: URLSession, task: URLSessionTask,
                    willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest,
                    completionHandler: @escaping (URLRequest?) -> Void) { completionHandler(nil) }
}

actor VehicleService {
    private var lastStart: Date?
    func lookup(_ input: String) async throws -> Vehicle {
        let plate = try VehicleParser.normalize(input)
        if let lastStart, Date().timeIntervalSince(lastStart) < 10 {
            throw LookupFailure(message: "Please wait ten seconds between lookups.")
        }
        lastStart = Date()
        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = 20
        configuration.timeoutIntervalForResource = 30
        configuration.httpCookieStorage = nil
        configuration.urlCache = nil
        let session = URLSession(configuration: configuration, delegate: NoRedirects(), delegateQueue: nil)
        defer { session.invalidateAndCancel() }
        var request = URLRequest(url: URL(string: "https://www.carinfo.app/rc-details/\(plate)")!)
        request.setValue("VehicleLookup/1.0", forHTTPHeaderField: "User-Agent")
        request.setValue("text/html", forHTTPHeaderField: "Accept")
        let (bytes, response) = try await session.bytes(for: request)
        guard let http = response as? HTTPURLResponse else { throw LookupFailure(message: "Unexpected response from CarInfo.") }
        guard http.statusCode == 200 else {
            let messages = [401: "CarInfo requires login.", 403: "CarInfo blocked automated access.",
                            404: "That vehicle page could not be found.", 429: "CarInfo is limiting requests. Try again later."]
            throw LookupFailure(message: messages[http.statusCode] ?? "CarInfo returned HTTP \(http.statusCode). Open the source in Safari.")
        }
        guard http.mimeType == "text/html" else { throw LookupFailure(message: "Unexpected response format from CarInfo.") }
        let limit = 3_000_000
        guard http.expectedContentLength <= Int64(limit) else { throw LookupFailure(message: "The response exceeded the size limit.") }
        var data = Data()
        for try await byte in bytes {
            try Task.checkCancellation()
            guard data.count < limit else { throw LookupFailure(message: "The response exceeded the size limit.") }
            data.append(byte)
        }
        guard let html = String(data: data, encoding: .utf8) else { throw LookupFailure(message: "The page uses an unsupported text encoding.") }
        return try VehicleParser.parse(html, plate: plate)
    }
}
