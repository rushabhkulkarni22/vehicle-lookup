import SwiftUI

@main
struct FindVehicleApp: App {
    var body: some Scene { WindowGroup { LookupView() } }
}

@MainActor
final class LookupModel: ObservableObject {
    @Published var plate = ""
    @Published var vehicle: Vehicle?
    @Published var error: String?
    @Published var loading = false
    @Published var sourceURL: URL?
    private let service = VehicleService()
    private var task: Task<Void, Never>?

    func search() {
        guard !loading else { return }
        vehicle = nil; error = nil; sourceURL = nil
        let normalized: String
        do { normalized = try VehicleParser.normalize(plate) }
        catch { self.error = error.localizedDescription; return }
        plate = normalized
        sourceURL = URL(string: "https://www.carinfo.app/rc-details/\(normalized)")
        loading = true
        task = Task {
            defer { loading = false; task = nil }
            do { vehicle = try await service.lookup(normalized) }
            catch is CancellationError { self.error = "Lookup cancelled." }
            catch let failure as URLError where failure.code == .cancelled { self.error = "Lookup cancelled." }
            catch { self.error = error.localizedDescription }
        }
    }

    func cancel() { task?.cancel() }
}

struct LookupView: View {
    @StateObject private var model = LookupModel()
    @FocusState private var editing: Bool
    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Label("Vehicle details, on your iPhone", systemImage: "car.fill")
                        .font(.headline).foregroundStyle(.teal)
                    Text("Search public CarInfo information. Owner names stay masked.")
                        .foregroundStyle(.secondary)
                }
                Section("Registration number") {
                    TextField("MH12XQ4561", text: $model.plate)
                        .textInputAutocapitalization(.characters).autocorrectionDisabled()
                        .keyboardType(.asciiCapable).submitLabel(.search)
                        .focused($editing).disabled(model.loading)
                        .onSubmit { editing = false; model.search() }
                        .accessibilityLabel("Registration number")
                    if model.loading {
                        HStack { ProgressView(); Text("Checking CarInfo…"); Spacer(); Button("Cancel", role: .cancel) { model.cancel() } }
                    } else {
                        Button { editing = false; model.search() } label: {
                            Label("Find vehicle", systemImage: "magnifyingglass")
                        }.disabled(model.plate.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    }
                }
                if let error = model.error {
                    Section { Label(error, systemImage: "exclamationmark.triangle").foregroundStyle(.orange) }
                }
                if let vehicle = model.vehicle {
                    Section(vehicle.plate) {
                        ForEach(Vehicle.labels, id: \.self) { label in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(label == "Owner Name" ? "Owner (masked)" : label).font(.caption).foregroundStyle(.secondary)
                                Text(vehicle.fields[label] ?? "Unavailable").textSelection(.enabled)
                            }.padding(.vertical, 3)
                        }
                    }
                    Section { Text("Retrieved \(vehicle.retrievedAt.formatted())").font(.caption).foregroundStyle(.secondary) }
                }
                if let url = model.sourceURL {
                    Section { Link(destination: url) { Label("Open source in Safari", systemImage: "safari") } }
                }
                Section {
                    Text("Your registration number is sent directly to CarInfo. This app stores no lookup history. Results depend on CarInfo availability and may require browser access.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Find Vehicle").tint(.teal)
        }
    }
}
