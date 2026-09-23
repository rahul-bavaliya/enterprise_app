from app.services.branch_import import clean_branch_row


def test_clean_branch_row_normalizes_csv_values() -> None:
    row = {
        "Branch Name": "  adelaide  ",
        "Branch Number": "20",
        "Address1": "23/25 Matthews Rd",
        "Branch City": "gepps cross",
        "Branch Province": "SA",
        "PostalCode": "5094",
        "Branch Country": "AU",
        "Region Name": "Australia",
        "Latitude": "-34.83618692",
        "Longitude": "138.6060488",
        "BranchJoinKey": "207",
        "Telephone1": "(519) 622-7799",
        "Division Name": "South Australia",
        "LOBName": "AU-AG",
    }

    cleaned = clean_branch_row(row)

    assert cleaned["name"] == "Adelaide"
    assert cleaned["number"] == 20
    assert cleaned["city"] == "Gepps Cross"
    assert cleaned["province"] == "South Australia"
    assert cleaned["country"] == "Australia"
    assert cleaned["postal_code"] == "5094"
    assert cleaned["join_key"] == 207
    assert cleaned["phone"] == "(519) 622-7799"
    assert cleaned["division_name"] == "South Australia"
    assert cleaned["lob_name"] == "AU-AG"
