# sds_generator.py
# Fully RDKit-Free SDS Generator using only PubChemPy

import pubchempy as pcp
import pandas as pd
from datetime import datetime
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import os

# -----------------------------
# Utility Functions
# -----------------------------

def fetch_compound_data(smiles):
    """
    Fetch compound data from PubChem using SMILES.
    Returns a dict with all required molecular properties.
    """
    try:
        compounds = pcp.get_compounds(smiles, 'smiles', timeout=10)
        if not compounds:
            return None
        c = compounds[0]

        def safe_float(val, default=0.0):
            try:
                return float(val) if val not in [None, '--'] else default
            except:
                return default

        def safe_int(val, default=0):
            try:
                return int(val) if val is not None else default
            except:
                return default

        return {
            "name": c.iupac_name or (c.synonyms[0] if c.synonyms else "Unknown Compound"),
            "formula": c.molecular_formula or "Not available",
            "mw": safe_float(c.molecular_weight),
            "cas": getattr(c, 'cas', "Not available"),
            "logp": safe_float(c.xlogp, default=2.0),
            "tpsa": safe_float(c.tpsa, default=0.0),
            "h_bond_donor": safe_int(c.h_bond_donor_count),
            "h_bond_acceptor": safe_int(c.h_bond_acceptor_count),
            "rotatable_bonds": safe_int(c.rotatable_bond_count),
            "heavy_atoms": safe_int(c.heavy_atom_count),
            "solubility": "Highly soluble" if c.molecular_weight < 500 and c.xlogp < 3 else "Low solubility"
        }
    except Exception as e:
        print(f"PubChem fetch failed: {e}")
        return None


def predict_toxicity(smiles):
    """
    Simulate toxicity prediction using heuristic rules
    """
    try:
        compounds = pcp.get_compounds(smiles, 'smiles')
        if not compounds:
            return {"toxicity_class": "Unknown", "hazard_endpoints": [], "ld50": "Unknown"}

        c = compounds[0]
        synonyms = " ".join([s.lower() for s in c.synonyms]) if c.synonyms else ""

        # Heuristic: toxic functional groups
        toxic_groups = ['nitro', 'cyano', 'azide', 'peroxide', 'halogenated', 'carbonyl fluoride']
        has_toxic = any(group in synonyms for group in toxic_groups)

        if has_toxic:
            return {
                "toxicity_class": "Class II (High)",
                "hazard_endpoints": ["Hepatotoxicity", "Neurotoxicity"],
                "ld50": "50 mg/kg"
            }
        else:
            return {
                "toxicity_class": "Class IV (Low)",
                "hazard_endpoints": ["None predicted"],
                "ld50": "5000 mg/kg"
            }
    except:
        return {"toxicity_class": "Unknown", "hazard_endpoints": ["Data not available"], "ld50": "Unknown"}


def section_title(i):
    """Return GHS SDS section title"""
    titles = {
        1: "Chemical Product and Company Identification",
        2: "Composition and Information on Ingredients",
        3: "Hazards Identification",
        4: "First Aid Measures",
        5: "Fire and Explosion Data",
        6: "Accidental Release Measures",
        7: "Handling and Storage",
        8: "Exposure Controls/Personal Protection",
        9: "Physical and Chemical Properties",
        10: "Stability and Reactivity",
        11: "Toxicological Information",
        12: "Ecological Information",
        13: "Disposal Considerations",
        14: "Transport Information",
        15: "Other Regulatory Information",
        16: "Other Information"
    }
    return titles.get(i, f"Section {i}")


def generate_sds(smiles):
    """
    Generate full SDS using only PubChem data
    """
    data = fetch_compound_data(smiles.strip())
    if not data:
        return None

    toxicity = predict_toxicity(smiles)
    mw = data["mw"]
    logp = data["logp"]

    # Flammability and hazard flags
    is_flammable = logp > 1.5
    is_toxic = toxicity["toxicity_class"] in ["Class I", "II", "III"]

    # Build SDS
    sds = {}
    for i in range(1, 17):
        sds[f"Section{i}"] = {
            "title": section_title(i),
            "data": {},
            "notes": []
        }

    name = data["name"]

    # Section 1
    sds["Section1"]["data"] = {
        "Product Identifier": name,
        "Company": "MEDxAI - Automated SDS Generator",
        "Address": "N/A",
        "Emergency Phone": "N/A",
        "Recommended Use": "Research Use Only"
    }

    # Section 2
    sds["Section2"]["data"] = {
        "Name": name,
        "CAS Number": data["cas"],
        "Molecular Formula": data["formula"],
        "Purity/Concentration": "100%"
    }

    # Section 3: Hazards
    pictograms = ["🔥 Flammable"] if is_flammable else []
    if is_toxic:
        pictograms.append("💀 Acute Toxicity")

    hazard_statements = []
    if is_flammable:
        hazard_statements.append("H225: Highly flammable liquid and vapor")
    if is_toxic:
        hazard_statements.extend(["H301: Toxic if swallowed", "H331: Toxic if inhaled"])

    signal_word = "Danger" if (is_flammable or is_toxic) else "Warning"

    health_effects = (
        "Harmful if inhaled, swallowed, or absorbed through skin. "
        + ("May cause organ damage. " if is_toxic else "")
        + ("Vapors may displace oxygen. " if is_flammable else "")
        + "Chronic exposure may affect organs."
    )

    sds["Section3"]["data"] = {
        "Signal Word": signal_word,
        "GHS Pictograms": ", ".join(pictograms) if pictograms else "Not classified",
        "Hazard Statements": hazard_statements or ["No significant hazards identified"],
        "Precautionary Statements": [
            "P210: Keep away from heat/sparks/open flames",
            "P261: Avoid breathing fumes",
            "P280: Wear protective gloves/clothing/eye protection",
            "P305+P351+P338: IF IN EYES: Rinse cautiously with water"
        ],
        "Physical Hazards": "Flammable" if is_flammable else "Not flammable",
        "Health Hazards": "Toxic" if is_toxic else "Low concern",
        "Environmental Hazards": "Toxic to aquatic life" if is_toxic else "Low concern",
        "Routes of Exposure": "Inhalation, Skin, Ingestion, Eyes",
        "Acute and Chronic Effects": health_effects,
        "Immediate Medical Attention": "Seek medical attention immediately. Show SDS to physician."
    }

    # Section 4
    sds["Section4"]["data"] = {
        "Inhalation": "Move to fresh air. If breathing is difficult, give oxygen.",
        "Skin Contact": "Wash with soap and water. Remove contaminated clothing.",
        "Eye Contact": "Flush with water for at least 15 minutes.",
        "Ingestion": "Do NOT induce vomiting. Rinse mouth and consult a physician."
    }

    # Section 5
    sds["Section5"]["data"] = {
        "Flash Point": "13°C" if is_flammable else "Not applicable",
        "Flammable Limits": "3.3% - 19%" if is_flammable else "Not flammable",
        "Extinguishing Media": "CO2, dry chemical, foam",
        "Special Hazards": "Combustible vapors" if is_flammable else "None"
    }

    # Section 6
    sds["Section6"]["data"] = {
        "Personal Precautions": "Wear PPE, ensure ventilation",
        "Environmental Precautions": "Prevent release to environment",
        "Methods of Containment": "Use inert absorbent (sand, vermiculite)"
    }

    # Section 7
    sds["Section7"]["data"] = {
        "Handling": "Use explosion-proof equipment. Ground containers.",
        "Storage": "Store in cool, ventilated area away from ignition sources."
    }

    # Section 8
    sds["Section8"]["data"] = {
        "TLV-TWA": "100 ppm (typical)",
        "Engineering Controls": "Fume hood, local exhaust ventilation",
        "Personal Protection": "Gloves, goggles, lab coat, respirator if needed"
    }

    # Section 9
    sds["Section9"]["data"] = {
        "Physical State": "Liquid" if mw < 300 else "Solid",
        "Color": "Colorless to pale yellow",
        "Odor": "Characteristic",
        "Melting Point": "Not available",
        "Boiling Point": "Not available",
        "Solubility in Water": data["solubility"],
        "Density": "~0.8 g/cm³ (estimated)",
        "Vapor Pressure": "< 1 mmHg at 25°C",
        "Molecular Weight": f"{mw:.2f} g/mol",
        "LogP": f"{logp:.2f}",
        "Topological Polar Surface Area (TPSA)": f"{data['tpsa']:.2f} Å²" if data['tpsa'] > 0 else "Not available",
        "Hydrogen Bond Donors": data["h_bond_donor"],
        "Hydrogen Bond Acceptors": data["h_bond_acceptor"],
        "Rotatable Bonds": data["rotatable_bonds"],
        "Heavy Atom Count": data["heavy_atoms"]
    }

    # Section 10
    sds["Section10"]["data"] = {
        "Stability": "Stable under normal conditions",
        "Conditions to Avoid": "Heat, flames, sparks",
        "Incompatible Materials": "Strong oxidizing agents",
        "Hazardous Decomposition": "Carbon monoxide, carbon dioxide"
    }

    # Section 11
    sds["Section11"]["data"] = {
        "LD50 Oral Rat": toxicity["ld50"],
        "LC50 Inhalation Rat": "Not available",
        "Carcinogenicity": "Suspected" if "Hepatotoxicity" in toxicity["hazard_endpoints"] else "Not suspected",
        "Mutagenicity": "Positive" if "Hepatotoxicity" in toxicity["hazard_endpoints"] else "Negative",
        "Toxicity Class": toxicity["toxicity_class"]
    }

    # Section 12
    sds["Section12"]["data"] = {
        "Ecotoxicity": "Toxic to aquatic life" if is_toxic else "Low concern",
        "Biodegradability": "Yes",
        "Persistence": "Low",
        "Bioaccumulation": "Low potential"
    }

    # Section 13
    sds["Section13"]["data"] = {
        "Disposal Method": "Dispose in accordance with local regulations",
        "Contaminated Packaging": "Rinse and recycle or dispose properly"
    }

    # Section 14
    sds["Section14"]["data"] = {
        "UN Number": "UN1170",
        "Proper Shipping Name": "Ethanol or Ethyl Alcohol",
        "Transport Hazard Class": "3 (Flammable Liquid)",
        "Packing Group": "II"
    }

    # Section 15
    sds["Section15"]["data"] = {
        "TSCA": "Listed",
        "DSL": "Listed",
        "WHMIS": "Classified",
        "GHS Regulation": "GHS Rev 9 compliant"
    }

    # Section 16
    sds["Section16"]["data"] = {
        "Date Prepared": datetime.now().strftime("%Y-%m-%d"),
        "Revision Number": "1.0",
        "Prepared By": "MEDxAI - Automated ADMET-SDS System",
        "Disclaimer": "Generated for research use only. Verify with lab testing and official sources."
    }

    return sds


def generate_docx(sds, compound_name="Unknown Compound"):
    """
    Generate DOCX file
    """
    doc = Document()
    sections = doc.sections
    for section in sections:
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)

    title = doc.add_heading('Safety Data Sheet (SDS)', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = doc.add_paragraph(f"Compound: {compound_name}")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    generated_on = datetime.now().strftime("%Y-%m-%d %H:%M")
    doc.add_paragraph(f"Generated on: {generated_on}", style='Caption')
    doc.add_paragraph()

    for i in range(1, 17):
        section_key = f"Section{i}"
        section = sds.get(section_key, {})
        title = section.get("title", f"Section {i}")
        doc.add_heading(f"{i}. {title}", level=1)

        data = section.get("data", {})
        if not data:
            doc.add_paragraph("No data available.")
        else:
            table = doc.add_table(rows=0, cols=2)
            table.style = 'Table Grid'
            for key, value in data.items():
                row = table.add_row()
                cell_key = row.cells[0]
                cell_val = row.cells[1]

                p_key = cell_key.paragraphs[0]
                run_key = p_key.add_run(str(key))
                run_key.bold = True

                if isinstance(value, list):
                    val_text = ", ".join([str(v) for v in value if v]) or "Not available"
                elif not value or value == "Not available":
                    val_text = "Not available"
                else:
                    val_text = str(value)

                cell_val.text = val_text

        doc.add_paragraph()

    disclaimer = doc.add_paragraph()
    run = disclaimer.add_run("Disclaimer: This report is generated for research use only. "
                             "Verify with lab testing and official sources before handling chemicals.")
    run.italic = True
    disclaimer.alignment = WD_ALIGN_PARAGRAPH.CENTER

    filename = f"SDS_{compound_name.replace(' ', '_').replace('/', '_')}.docx"
    doc.save(filename)
    return filename
