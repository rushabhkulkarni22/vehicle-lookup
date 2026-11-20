import XCTest
@testable import FindVehicle

final class VehicleParserTests: XCTestCase {
    private let plate = "MH12XQ4561"
    private func page(_ extra: String = "") -> String {
        "<html><body><p>MH12XQ4561</p><b>Make &amp; Model</b><span>Example Car</span>\(extra)</body></html>"
    }
    func testNormalization() throws {
        XCTAssertEqual(try VehicleParser.normalize("mh12 xq-4561"), plate)
        XCTAssertEqual(try VehicleParser.normalize("22BH1234AA"), "22BH1234AA")
        XCTAssertThrowsError(try VehicleParser.normalize("../../login"))
    }
    func testOnlyMaskedNames() {
        XCTAssertEqual(VehicleParser.maskedName("A*** B***"), "A*** B***")
        XCTAssertNil(VehicleParser.maskedName("Example Person"))
        XCTAssertNil(VehicleParser.maskedName("Example P***"))
        XCTAssertNil(VehicleParser.maskedName("+919999999999"))
    }
    func testSafeFieldsAndEntities() throws {
        let result = try VehicleParser.parse(page("<b>Owner Name</b><i>A*** B***</i><b>Phone</b><i>9999999999</i>"), plate: plate)
        XCTAssertEqual(result.fields["Make & Model"], "Example Car")
        XCTAssertEqual(result.fields["Owner Name"], "A*** B***")
        XCTAssertNil(result.fields["Phone"])
    }
    func testHiddenAndFullNamesExcluded() throws {
        let hidden = "<script>Owner Name Secret Person</script><div hidden><b>Owner Name</b><i>A*** B***</i></div><div style='display: none'><b>Owner Name</b><i>C*** D***</i></div><b>Owner Name</b><i>Example Person</i>"
        XCTAssertNil(try VehicleParser.parse(page(hidden), plate: plate).fields["Owner Name"])
    }
    func testWrongPlateAndChallenge() {
        XCTAssertThrowsError(try VehicleParser.parse(page(), plate: "MH12AB1234"))
        XCTAssertThrowsError(try VehicleParser.parse(page("<p>Verify you are human</p>"), plate: plate))
        XCTAssertThrowsError(try VehicleParser.parse("<p>MH12XQ4561</p>", plate: plate))
    }
    func testInsurance() throws {
        let result = try VehicleParser.parse(page("<p>Insurance Expiring on 04-Dec-2026</p>"), plate: plate)
        XCTAssertEqual(result.fields["Insurance Validity"], "04-Dec-2026")
    }
}
