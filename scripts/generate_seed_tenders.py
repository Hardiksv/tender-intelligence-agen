import os
import json
import fitz  # PyMuPDF
from datetime import datetime, timedelta, timezone

SEED_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw")
os.makedirs(SEED_DIR, exist_ok=True)

# 10 Detailed Bus Operations Tenders
SEED_TENDERS_DATA = [
    {
        "filename": "tender_001.pdf",
        "title": "Procurement and Operation of 100 Electric Buses on Gross Cost Contract (GCC) Model in Jaipur",
        "issuing_authority": "Jaipur City Transport Services Limited (JCTSL)",
        "city": "Jaipur",
        "state": "Rajasthan",
        "category": "bus_operations",
        "submission_deadline": "2026-09-15T15:00:00+05:30",
        "emd_amount": 5000000.0,
        "document_fee": 25000.0,
        "source_url": "https://eproc.rajasthan.gov.in/tenders/jctsl-gcc-100-ebuses",
        "source_name": "Rajasthan e-Procurement Portal",
        "pages": [
            "SECTION 1: NOTICE INVITING TENDER (NIT)\nTender Ref No: JCTSL/2026/GCC/100-EBUS\nJaipur City Transport Services Limited invites competitive bids for the Procurement, Operation, and Maintenance of 100 AC Electric Buses (12m Midi/Standard) on Gross Cost Contract (GCC) basis for a period of 10 years in Jaipur City.\nSubmission Deadline: 15-September-2026 15:00 IST.\nEMD Amount: INR 50,00,000/- (Rupees Fifty Lakhs only).\nTender Fee: INR 25,000/-.",
            "SECTION 2: ELIGIBILITY CRITERIA & QUALIFICATION REQUIREMENTS\n2.1 Technical Fleet Experience:\nThe bidder must have operated a minimum fleet size of 80 commercial buses (diesel/CNG/electric) continuously for at least 3 years prior to bid submission date.\n\n2.2 Financial Turnover:\nThe minimum annual turnover of the bidder should be at least INR 120,00,000,00 (Rupees 120 Crore) in any three of the last five financial years.\n\n2.3 Past Contract Value:\nThe bidder should have executed a single past bus operation contract worth at least INR 60,00,000,00 (Rupees 60 Crore).\n\n2.4 Experience:\nMinimum 5 years of experience in urban public transit operations.",
            "SECTION 3: SCOPE OF WORK\nThe operator shall be responsible for daily bus scheduling, driver deployment, charging infrastructure setup, battery maintenance, route adherence, and passenger safety compliance as mandated by JCTSL."
        ]
    },
    {
        "filename": "tender_002.pdf",
        "title": "Selection of Bus Operator for 50 Midi Non-AC Diesel Buses on Wet Lease Basis in Gurugram",
        "issuing_authority": "Gurugram Metropolitan City Bus Limited (GMCBL)",
        "city": "Gurugram",
        "state": "Haryana",
        "category": "bus_operations",
        "submission_deadline": "2026-09-01T17:00:00+05:30",
        "emd_amount": 2500000.0,
        "document_fee": 10000.0,
        "source_url": "https://eproc.haryana.gov.in/gmcbl-wetlease-50",
        "source_name": "Haryana e-Procurement Portal",
        "pages": [
            "GURUGRAM METROPOLITAN CITY BUS LIMITED (GMCBL)\nINVITATION FOR BIDS: WET LEASE BUS OPERATIONS\nTender ID: GMCBL/WL/2026/050\nScope: Operation of 50 Midi Non-AC Diesel Buses on wet lease basis per-km rate in Gurugram urban area.\nBid Submission Closing Date: 01-September-2026 17:00 IST.\nEMD: Rs. 25,00,000 (Twenty Five Lakhs INR).\nDocument Fee: Rs. 10,000.",
            "ELIGIBILITY CRITERIA:\n- Minimum Fleet Size: The bidder must own/lease and operate at least 40 buses.\n- Turnover: Minimum average annual turnover of Rs. 40 Crore (INR 400,000,000) over the last 3 financial years.\n- Minimum Operating Experience: 3 years in public or private stage carriage operations.\n- Preferred Geographies: Bidders with operating depots in Haryana, Delhi NCR, or Punjab will be given preference.",
            "SCOPE & OPERATIONAL TERMS:\nGMCBL will collect fare revenue. Operator will be paid fixed per-kilometer rate subject to 95% fleet availability penalty clause."
        ]
    },
    {
        "filename": "tender_003.pdf",
        "title": "Contract for Per-Kilometer Operation of 200 CNG Intra-City Buses in Ahmedabad",
        "issuing_authority": "Ahmedabad Janmarg Limited (AJL / BRTS)",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "category": "bus_operations",
        "submission_deadline": "2026-08-28T16:00:00+05:30",
        "emd_amount": 10000000.0,
        "document_fee": 50000.0,
        "source_url": "https://eprocure.gov.in/ajl-ahmedabad-200-cng",
        "source_name": "Central Public Procurement Portal (CPPP)",
        "pages": [
            "AHMEDABAD JANMARG LIMITED (BRTS)\nTENDER NOTICE NO: AJL/OPS/CNG/200/2026\nSubject: Request for Proposal (RFP) for Operation and Maintenance of 200 Low-Floor CNG Buses on Per-Km Service Contract for 8 Years.\nSubmission Deadline: 28-August-2026 16:00 Hrs IST.\nEMD: INR 1,00,00,000 (Rupees One Crore).\nTender Fee: INR 50,000.",
            "QUALIFICATION REQUIREMENTS:\n1. Minimum Fleet Size: Bidder must have operated a total of at least 150 commercial buses.\n2. Financial Turnover: Annual turnover must not be less than INR 180 Crore in each of the past 3 fiscal years.\n3. Experience: Minimum 7 years of successful experience in running BRTS / City Bus services.\n4. Mandatory Past Contract: At least one completed past contract worth INR 100 Crore in transport sector.",
            "DETAILED SCOPE:\nOperator shall deploy qualified drivers, manage depot washing, and maintain peak hour frequency adherence."
        ]
    },
    {
        "filename": "tender_004.pdf",
        "title": "Operation and Maintenance of 75 Electric City Buses under GCC in Lucknow",
        "issuing_authority": "Lucknow Mahanagar Parivahan Sewa Limited (LMPSL)",
        "city": "Lucknow",
        "state": "Uttar Pradesh",
        "category": "bus_operations",
        "submission_deadline": "2026-10-05T14:00:00+05:30",
        "emd_amount": 3500000.0,
        "document_fee": 15000.0,
        "source_url": "https://etender.up.nic.in/lmpsl-ebus-75",
        "source_name": "UP e-Procurement Portal",
        "pages": [
            "LUCKNOW MAHANAGAR PARIVAHAN SEWA LIMITED\nTender Document: LMPSL/GCC/E-BUS/75/2026\nOperation of 75 Electric Buses under Gross Cost Contract Model in Lucknow Municipal Area.\nSubmission Deadline: 05-October-2026 14:00 IST.\nEMD: Rs. 35 Lakhs. Document Fee: Rs. 15,000.",
            "ELIGIBILITY CONDITIONS:\n- Minimum Fleet: Operator must manage at least 50 buses.\n- Turnover: Minimum average turnover of INR 50 Crore during 2023-2026.\n- Experience: 4 years minimum in passenger transportation.\n- Past Contract Value: Single past contract minimum INR 25 Crore.",
            "TECHNICAL SPECIFICATIONS:\nCharging infrastructure space provided by authority; electricity charges borne by authority as per GCC terms."
        ]
    },
    {
        "filename": "tender_005.pdf",
        "title": "Wet Lease Bus Operation Contract for 150 Mini Electric Buses in Pune",
        "issuing_authority": "Pune Mahanagar Parivahan Mahamandal Limited (PMPML)",
        "city": "Pune",
        "state": "Maharashtra",
        "category": "bus_operations",
        "submission_deadline": "2026-09-20T18:00:00+05:30",
        "emd_amount": 7500000.0,
        "document_fee": 30000.0,
        "source_url": "https://mahatenders.gov.in/pmpml-150-mini-ebus",
        "source_name": "Maharashtra Tenders Portal",
        "pages": [
            "PUNE MAHANAGAR PARIVAHAN MAHAMANDAL LIMITED (PMPML)\nNOTICE INVITING TENDER: PMPML/CIVIL/OPS/2026/150\nSelection of Private Bus Operators for 150 Mini AC Electric Buses on Wet Lease Fee Per Km Basis for Pune Metro Feeder Routes.\nClosing Date: 20-September-2026 18:00 IST.\nEMD: Rs 75,00,000. Tender Fee: Rs 30,000.",
            "ELIGIBILITY MANDATES:\n- Fleet Experience: Minimum fleet size of 100 operating buses.\n- Annual Turnover: Minimum INR 100 Crore in any 2 of last 3 years.\n- Experience: Minimum 5 years operating fleet in India.\n- Past Contract: Minimum Rs 50 Crore single contract executed.",
            "OPERATIONAL PARAMETERS:\nGuaranteed daily distance of 200 km per bus. Penalty of Rs 5000 per breakdown."
        ]
    },
    {
        "filename": "tender_006.pdf",
        "title": "Selection of Operator for 120 CNG Bus Operations under GCC in Bhopal",
        "issuing_authority": "Bhopal City Link Limited (BCLL)",
        "city": "Bhopal",
        "state": "Madhya Pradesh",
        "category": "bus_operations",
        "submission_deadline": "2026-09-10T15:30:00+05:30",
        "emd_amount": 4500000.0,
        "document_fee": 20000.0,
        "source_url": "https://mptenders.gov.in/bcll-bhopal-120-cng",
        "source_name": "MP Tenders Portal",
        "pages": [
            "BHOPAL CITY LINK LIMITED (BCLL)\nRFP NO: BCLL/2026/GCC/120\nOperation and Maintenance of 120 Low-Floor CNG Buses for Bhopal Urban Transport Network.\nLast Date of Submission: 10-September-2026 15:30 IST.\nEMD: INR 45 Lakhs. Tender Fee: INR 20,000.",
            "QUALIFICATION CRITERIA:\n1. Minimum Fleet: 70 commercial operating buses.\n2. Turnover: Minimum annual turnover Rs 70 Crore (INR 700,000,000).\n3. Experience: Minimum 4 years experience.\n4. Past Contract: Single contract of at least INR 35 Crore value.",
            "SCOPE:\nOperator provides drivers, fuel management, depot operations, IT ticketing integration."
        ]
    },
    {
        "filename": "tender_007.pdf",
        "title": "Procurement and Operation of 60 Electric Standard Buses on GCC in Chandigarh",
        "issuing_authority": "Chandigarh Transport Undertaking (CTU)",
        "city": "Chandigarh",
        "state": "Chandigarh",
        "category": "bus_operations",
        "submission_deadline": "2026-08-30T13:00:00+05:30",
        "emd_amount": 3000000.0,
        "document_fee": 12000.0,
        "source_url": "https://eprocure.gov.in/ctu-chandigarh-60-ebus",
        "source_name": "CPPP",
        "pages": [
            "CHANDIGARH TRANSPORT UNDERTAKING (CTU)\nTENDER NOTICE: CTU/E-BUS/2026/060\nOperation of 60 Electric Buses (12m AC) on Gross Cost Contract (GCC) in Chandigarh Tricity.\nClosing Deadline: 30-August-2026 13:00 IST.\nEMD: Rs 30,00,000. Fee: Rs 12,000.",
            "MANDATORY REQUIREMENTS:\n- Minimum Fleet Size: 50 buses in past 3 years.\n- Turnover: Minimum INR 60 Crore per annum.\n- Experience: 4 years in fleet management.\n- Geography: Experience in Northern India preferred.",
            "COMMERCIAL TERMS:\nMonthly payment based on verified km operational logs."
        ]
    },
    {
        "filename": "tender_008.pdf",
        "title": "Wet Lease Contract for 80 Diesel Midi Stage Carriage Buses in Guwahati",
        "issuing_authority": "Assam State Transport Corporation (ASTC)",
        "city": "Guwahati",
        "state": "Assam",
        "category": "bus_operations",
        "submission_deadline": "2026-09-25T16:30:00+05:30",
        "emd_amount": 2000000.0,
        "document_fee": 8000.0,
        "source_url": "https://assamtenders.gov.in/astc-guwahati-80-midi",
        "source_name": "Assam Tenders",
        "pages": [
            "ASSAM STATE TRANSPORT CORPORATION (ASTC)\nNIT: ASTC/GW/2026/80-BUS\nOperation of 80 Midi Stage Carriage Diesel Buses on Wet Lease in Guwahati Metropolitan Area.\nClosing Date: 25-September-2026 16:30 IST.\nEMD: INR 20 Lakhs. Fee: INR 8,000.",
            "ELIGIBILITY:\n- Minimum Fleet: 30 operating buses.\n- Annual Turnover: INR 25 Crore minimum.\n- Experience: 3 years in passenger transport.\n- Past Contract: Rs 15 Crore single executed contract.",
            "REVENUE & MONITORING:\nGPS tracking mandatory; ticketing managed through ETM system."
        ]
    },
    {
        "filename": "tender_009.pdf",
        "title": "Per-Km Bus Operation Contract for 110 AC CNG Buses in Surat",
        "issuing_authority": "Surat Sitilink Limited (Surat BRTS)",
        "city": "Surat",
        "state": "Gujarat",
        "category": "bus_operations",
        "submission_deadline": "2026-10-10T17:00:00+05:30",
        "emd_amount": 6000000.0,
        "document_fee": 25000.0,
        "source_url": "https://suratsitilink.org/tenders/cng-110-2026",
        "source_name": "Surat Municipal Portal",
        "pages": [
            "SURAT SITILINK LIMITED (BRTS)\nTender Ref: SITILINK/2026/CNG/110\nRequest for Proposal for Operation of 110 AC CNG Buses under Per-Km Contract Model.\nDeadline: 10-October-2026 17:00 IST.\nEMD: Rs 60 Lakhs. Tender Fee: Rs 25,000.",
            "ELIGIBILITY CRITERIA:\n- Minimum Fleet: 90 buses in continuous commercial operation.\n- Annual Turnover: Minimum INR 90 Crore.\n- Operating Experience: Minimum 5 years.\n- Past Contract Value: Single past contract minimum INR 45 Crore.",
            "PENALTY & PERFORMANCE:\nSLA metrics apply to timetable compliance and clean bus interiors."
        ]
    },
    {
        "filename": "tender_010.pdf",
        "title": "Operation of 250 Electric Buses on GCC Basis for Intercity Connectivity in Bengaluru",
        "issuing_authority": "Bengaluru Metropolitan Transport Corporation (BMTC)",
        "city": "Bengaluru",
        "state": "Karnataka",
        "category": "bus_operations",
        "submission_deadline": "2026-10-15T15:00:00+05:30",
        "emd_amount": 15000000.0,
        "document_fee": 100000.0,
        "source_url": "https://eproc.karnataka.gov.in/bmtc-250-ebus-gcc",
        "source_name": "Karnataka e-Procurement Portal",
        "pages": [
            "BENGALURU METROPOLITAN TRANSPORT CORPORATION (BMTC)\nTENDER NOTIFICATION: BMTC/EC/GCC/250/2026\nProcurement, Operation and Maintenance of 250 Non-AC & AC Electric Buses on Gross Cost Contract (GCC) for 12 Years.\nSubmission Deadline: 15-October-2026 15:00 IST.\nEMD Amount: INR 1,50,00,000 (One Crore Fifty Lakhs).\nDocument Fee: INR 1,00,000.",
            "ELIGIBILITY MANDATES:\n- Fleet Size Requirement: Minimum 200 buses operated in India.\n- Minimum Turnover: Average annual turnover of INR 250 Crore (Rs 2,500,000,000) over last 3 years.\n- Past Experience: 8 years in commercial bus transport operations.\n- Past Contract Value: Single completed contract of at least INR 125 Crore.",
            "INFRASTRUCTURE & PAYMENTS:\nBMTC will provide depot space and high-voltage grid connection; operator arranges chargers and staff."
        ]
    }
]


def generate_seed_pdfs():
    manifest = []
    print("Generating 10 real Bus Operations tender PDF documents...")

    for tender in SEED_TENDERS_DATA:
        filepath = os.path.join(SEED_DIR, tender["filename"])
        doc = fitz.open()

        for page_num, text in enumerate(tender["pages"], start=1):
            page = doc.new_page(width=595, height=842)  # A4 size
            # Add text to page
            rect = fitz.Rect(50, 50, 545, 792)
            page.insert_textbox(rect, text, fontsize=12, fontname="helv")

        doc.save(filepath)
        doc.close()

        manifest.append({
            "filename": tender["filename"],
            "raw_document_path": filepath,
            "title": tender["title"],
            "issuing_authority": tender["issuing_authority"],
            "city": tender["city"],
            "state": tender["state"],
            "category": tender["category"],
            "submission_deadline": tender["submission_deadline"],
            "emd_amount": tender["emd_amount"],
            "document_fee": tender["document_fee"],
            "source_url": tender["source_url"],
            "source_name": tender["source_name"]
        })
        print(f"  Created: {tender['filename']} ({len(tender['pages'])} pages)")

    manifest_path = os.path.join(SEED_DIR, "seed_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Seed manifest created at {manifest_path}")


if __name__ == "__main__":
    generate_seed_pdfs()
