"""
Agent Compliance Checker — Serverless Function fuer Vercel.
Prueft ob eine AI-Agent-Aktion GDPR/EU-AI-Act-konform ist.
Liefert Risikostufe, Anforderungen, Empfehlungen und anwendbare Gesetze.
"""

from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs


# EU AI Act Risikokategorien und Zeitplan
AI_ACT_TIMELINE = {
    "prohibited_practices": "2025-02-02",
    "governance_rules": "2025-08-02",
    "high_risk_obligations": "2026-08-02",
    "full_enforcement": "2027-08-02",
}

# Aktionstypen mit detaillierten Compliance-Infos
ACTION_REGISTRY = {
    "automated_decision": {
        "risk_level": "high",
        "allowed": True,
        "regulations": [
            "EU AI Act — Annex III (High-Risk AI Systems)",
            "GDPR Art. 22 — Automated Individual Decision-Making",
            "GDPR Art. 13/14 — Right to Information",
            "GDPR Art. 15 — Right of Access",
        ],
        "requirements": [
            "Human oversight mechanism required (Art. 14 AI Act)",
            "Right to explanation must be provided (GDPR Art. 22(3))",
            "Data subject can request human intervention",
            "Fundamental rights impact assessment (FRIA) mandatory",
            "Technical documentation per Annex IV AI Act",
            "Logging of all automated decisions for audit trail",
            "Transparency: inform data subjects about automated processing",
            "Regular accuracy and bias testing",
        ],
        "recommendations": [
            "Implement human-in-the-loop for consequential decisions",
            "Provide clear opt-out mechanism for automated processing",
            "Document decision logic in plain language",
            "Conduct DPIA (Data Protection Impact Assessment) before deployment",
            "Register in EU AI Database before market placement",
        ],
        "gdpr_articles": ["Art. 22", "Art. 13", "Art. 14", "Art. 15", "Art. 35"],
        "ai_act_category": "Annex III — High-Risk",
        "deadline": "2026-08-02",
    },
    "biometric_identification": {
        "risk_level": "unacceptable",
        "allowed": False,
        "regulations": [
            "EU AI Act Art. 5(1)(d) — Prohibited Real-Time Biometric ID in Public Spaces",
            "EU AI Act Art. 5(1)(f) — Prohibited Emotion Recognition in Workplace/Education",
            "GDPR Art. 9 — Processing of Special Categories (Biometric Data)",
            "EU Charter Art. 7 — Right to Private Life",
        ],
        "requirements": [
            "BANNED in public spaces for law enforcement (with narrow exceptions)",
            "BANNED for emotion recognition in workplace and education",
            "Post-remote biometric ID classified as high-risk (requires judicial authorization)",
            "Explicit consent required if used in private, controlled environments",
            "Biometric data is special category under GDPR — Art. 9(1) prohibition applies",
        ],
        "recommendations": [
            "Do NOT deploy real-time biometric identification in public spaces",
            "Seek legal counsel before any biometric processing",
            "If private use: obtain explicit, informed, freely given consent",
            "Consider privacy-preserving alternatives (on-device processing)",
            "Conduct mandatory FRIA and DPIA before any deployment",
        ],
        "gdpr_articles": ["Art. 9", "Art. 35", "Art. 36"],
        "ai_act_category": "Art. 5 — Prohibited Practice",
        "deadline": "2025-02-02",
    },
    "credit_scoring": {
        "risk_level": "high",
        "allowed": True,
        "regulations": [
            "EU AI Act — Annex III, 5(b) (Creditworthiness Assessment)",
            "GDPR Art. 22 — Right Not to be Subject to Automated Decision",
            "Consumer Credit Directive 2008/48/EC",
            "GDPR Art. 35 — DPIA Required",
        ],
        "requirements": [
            "Human oversight mandatory — no fully automated credit decisions",
            "Transparency: explain factors used in scoring",
            "Right to obtain human intervention on credit decisions",
            "Non-discrimination testing required (gender, ethnicity, age)",
            "Technical documentation per Annex IV",
            "Conformity assessment before deployment",
            "Post-market monitoring system required",
            "Logging of all scoring decisions",
        ],
        "recommendations": [
            "Use explainable AI models (avoid black-box scoring)",
            "Test for disparate impact across protected groups quarterly",
            "Provide applicants with score factors and improvement advice",
            "Register system in EU AI Database",
            "Implement appeal mechanism for rejected applicants",
        ],
        "gdpr_articles": ["Art. 22", "Art. 13", "Art. 14", "Art. 35"],
        "ai_act_category": "Annex III, 5(b) — High-Risk",
        "deadline": "2026-08-02",
    },
    "content_moderation": {
        "risk_level": "limited",
        "allowed": True,
        "regulations": [
            "EU AI Act Art. 50 — Transparency Obligations for Limited Risk",
            "Digital Services Act (DSA) — Content Moderation Transparency",
            "GDPR Art. 22 — if fully automated with legal effects",
        ],
        "requirements": [
            "Disclose that AI is used for content moderation",
            "Provide appeal mechanism for moderation decisions",
            "Publish transparency reports (DSA requirement for large platforms)",
            "Human review option for contested decisions",
            "Non-discrimination in moderation practices",
        ],
        "recommendations": [
            "Combine AI moderation with human review for edge cases",
            "Document moderation criteria and update regularly",
            "Provide clear community guidelines",
            "Track and report false positive/negative rates",
            "Offer multi-language support for appeals",
        ],
        "gdpr_articles": ["Art. 22"],
        "ai_act_category": "Art. 50 — Limited Risk (Transparency)",
        "deadline": "2025-08-02",
    },
    "recruitment": {
        "risk_level": "high",
        "allowed": True,
        "regulations": [
            "EU AI Act — Annex III, 4(a) (Recruitment and Selection)",
            "GDPR Art. 22 — Automated Decision-Making",
            "EU Employment Equality Directive 2000/78/EC",
            "GDPR Art. 9 — Special Categories (if processing ethnicity, health, etc.)",
        ],
        "requirements": [
            "Bias testing mandatory before deployment and regularly thereafter",
            "Human oversight required for all hiring decisions",
            "Candidates must be informed AI is used in selection",
            "Right to explanation for rejection decisions",
            "Fundamental rights impact assessment (FRIA)",
            "Technical documentation per Annex IV",
            "Conformity assessment required",
            "Post-market monitoring for bias drift",
        ],
        "recommendations": [
            "Audit training data for historical bias",
            "Test across gender, age, ethnicity, disability status",
            "Never use AI as sole decision-maker in hiring",
            "Provide candidates with feedback on AI assessment",
            "Keep human recruiter in the loop for final decisions",
        ],
        "gdpr_articles": ["Art. 22", "Art. 9", "Art. 13", "Art. 35"],
        "ai_act_category": "Annex III, 4(a) — High-Risk",
        "deadline": "2026-08-02",
    },
    "data_processing": {
        "risk_level": "limited",
        "allowed": True,
        "regulations": [
            "GDPR Art. 5 — Principles of Data Processing",
            "GDPR Art. 6 — Lawful Basis for Processing",
            "GDPR Art. 13/14 — Information Obligations",
        ],
        "requirements": [
            "Lawful basis required (consent, contract, legitimate interest, etc.)",
            "Purpose limitation — only process for stated purposes",
            "Data minimization — collect only what is necessary",
            "Storage limitation — define retention periods",
            "Integrity and confidentiality — secure processing",
            "Transparency — inform data subjects",
        ],
        "recommendations": [
            "Map all data flows and document processing activities",
            "Implement privacy by design and by default",
            "Conduct DPIA for high-risk processing",
            "Appoint a DPO if required by Art. 37",
            "Review lawful basis regularly",
        ],
        "gdpr_articles": ["Art. 5", "Art. 6", "Art. 13", "Art. 14", "Art. 30"],
        "ai_act_category": "Not directly classified — depends on AI usage context",
        "deadline": None,
    },
    "customer_profiling": {
        "risk_level": "limited",
        "allowed": True,
        "regulations": [
            "EU AI Act Art. 50 — Transparency Obligations",
            "GDPR Art. 21 — Right to Object to Profiling",
            "GDPR Art. 22 — Automated Profiling with Legal Effects",
            "ePrivacy Directive — Cookie/Tracking Consent",
        ],
        "requirements": [
            "Opt-out mechanism required for profiling",
            "Inform users about profiling activities",
            "Consent required for tracking cookies/pixels",
            "If profiling produces legal effects: GDPR Art. 22 applies fully",
            "Data minimization in profiling datasets",
        ],
        "recommendations": [
            "Offer granular opt-out (not just all-or-nothing)",
            "Use aggregated data where possible instead of individual profiling",
            "Review profiling logic for discriminatory outcomes",
            "Implement consent management platform (CMP)",
            "Allow users to access and correct their profiles",
        ],
        "gdpr_articles": ["Art. 21", "Art. 22", "Art. 13", "Art. 14"],
        "ai_act_category": "Art. 50 — Limited Risk (Transparency)",
        "deadline": "2025-08-02",
    },
    "chatbot_interaction": {
        "risk_level": "minimal",
        "allowed": True,
        "regulations": [
            "EU AI Act Art. 50(1) — AI System Disclosure",
            "GDPR Art. 13 — Information at Point of Collection",
        ],
        "requirements": [
            "Must disclose that user is interacting with an AI system",
            "Disclosure must be clear, timely, and understandable",
            "If collecting personal data: standard GDPR obligations apply",
        ],
        "recommendations": [
            "Place AI disclosure prominently before interaction begins",
            "Offer option to speak with human agent",
            "Do not design chatbot to deceive about its nature",
            "Log interactions for quality assurance with user consent",
            "Provide clear escalation path to human support",
        ],
        "gdpr_articles": ["Art. 13"],
        "ai_act_category": "Art. 50(1) — Minimal Risk (Transparency Only)",
        "deadline": "2025-08-02",
    },
    "medical_diagnosis": {
        "risk_level": "high",
        "allowed": True,
        "regulations": [
            "EU AI Act — Annex III, 5(c) (Medical Devices with AI)",
            "Medical Device Regulation (MDR) 2017/745",
            "GDPR Art. 9 — Special Categories (Health Data)",
            "GDPR Art. 35 — DPIA Required",
        ],
        "requirements": [
            "CE marking potentially required under MDR",
            "Clinical evaluation and validation studies",
            "Quality management system (QMS) per MDR",
            "Human oversight by qualified medical professional mandatory",
            "Explicit consent for health data processing (GDPR Art. 9(2)(a))",
            "Technical documentation per Annex IV AI Act + MDR Annex II",
            "Post-market surveillance system",
            "Incident reporting obligations",
        ],
        "recommendations": [
            "Engage Notified Body early for conformity assessment",
            "Validate AI model on diverse patient populations",
            "Never position AI as replacement for medical professional",
            "Implement continuous learning monitoring with human approval",
            "Maintain detailed audit trail of all diagnoses",
        ],
        "gdpr_articles": ["Art. 9", "Art. 35", "Art. 36"],
        "ai_act_category": "Annex III, 5(c) — High-Risk (Medical Device)",
        "deadline": "2026-08-02",
    },
    "autonomous_driving": {
        "risk_level": "high",
        "allowed": True,
        "regulations": [
            "EU AI Act — Annex III, 2(a) (Safety Components of Vehicles)",
            "EU Vehicle Safety Regulation 2019/2144",
            "Product Liability Directive (revised 2024)",
            "UNECE Regulations on Automated Driving",
        ],
        "requirements": [
            "Type-approval under EU Vehicle Safety Regulation",
            "Conformity assessment per AI Act",
            "Real-time monitoring and logging system",
            "Cybersecurity management system (UNECE R155)",
            "Software update management system (UNECE R156)",
            "Human override capability required",
            "Fundamental rights impact assessment",
            "Post-market monitoring and incident reporting",
        ],
        "recommendations": [
            "Implement redundant safety systems",
            "Test extensively in simulated and real-world conditions",
            "Establish clear liability framework with insurers",
            "Plan for over-the-air update governance",
            "Engage with national vehicle approval authorities early",
        ],
        "gdpr_articles": [],
        "ai_act_category": "Annex III, 2(a) — High-Risk (Safety Component)",
        "deadline": "2026-08-02",
    },
    "price_optimization": {
        "risk_level": "limited",
        "allowed": True,
        "regulations": [
            "EU AI Act Art. 50 — Transparency Obligations",
            "EU Competition Law (TFEU Art. 101/102)",
            "Consumer Rights Directive 2011/83/EU",
            "Omnibus Directive 2019/2161 — Price Transparency",
        ],
        "requirements": [
            "Anti-discrimination checks — no pricing based on protected characteristics",
            "Price transparency obligations under Omnibus Directive",
            "No algorithmic collusion (competition law)",
            "If personalized pricing: must inform consumer",
            "Prior price display required for promotions",
        ],
        "recommendations": [
            "Audit pricing algorithm for discriminatory patterns",
            "Document pricing logic for competition authority requests",
            "Implement price fairness monitoring",
            "Avoid sharing pricing algorithms with competitors",
            "Test for geographic or demographic discrimination",
        ],
        "gdpr_articles": ["Art. 22"],
        "ai_act_category": "Art. 50 — Limited Risk (Transparency)",
        "deadline": "2025-08-02",
    },
    "surveillance": {
        "risk_level": "unacceptable",
        "allowed": False,
        "regulations": [
            "EU AI Act Art. 5(1)(a) — Prohibited Subliminal/Manipulative Techniques",
            "EU AI Act Art. 5(1)(d) — Prohibited Real-Time Biometric ID",
            "EU AI Act Art. 5(1)(g) — Prohibited Untargeted Scraping for Facial Recognition",
            "EU Charter Art. 7 — Right to Private Life",
            "EU Charter Art. 8 — Right to Protection of Personal Data",
            "ECHR Art. 8 — Right to Respect for Private and Family Life",
        ],
        "requirements": [
            "BANNED: mass surveillance of public spaces in the EU",
            "BANNED: social scoring systems by public authorities",
            "BANNED: untargeted scraping of facial images from internet/CCTV",
            "BANNED: emotion recognition in workplace and education settings",
            "Very narrow law enforcement exceptions require judicial authorization",
        ],
        "recommendations": [
            "Do NOT deploy mass surveillance AI in EU jurisdiction",
            "If security monitoring needed: use non-biometric, proportionate methods",
            "Seek legal opinion before any monitoring system deployment",
            "Consider privacy-preserving security alternatives",
            "Review scope regularly to ensure proportionality",
        ],
        "gdpr_articles": ["Art. 9", "Art. 35"],
        "ai_act_category": "Art. 5 — Prohibited Practice",
        "deadline": "2025-02-02",
    },
}

# Datentyp-spezifische Regeln (fuer data_processing Aktion)
DATA_TYPE_RULES = {
    "personal": {
        "risk_level": "limited",
        "extra_requirements": [
            "Lawful basis required (GDPR Art. 6)",
            "Purpose limitation applies",
            "Data subject rights must be facilitated (Art. 15-22)",
        ],
    },
    "sensitive": {
        "risk_level": "high",
        "extra_requirements": [
            "Special category data under GDPR Art. 9",
            "Explicit consent or specific legal basis required",
            "DPIA mandatory (Art. 35)",
            "Enhanced security measures required",
        ],
    },
    "biometric": {
        "risk_level": "high",
        "extra_requirements": [
            "Biometric data is special category (Art. 9)",
            "Explicit consent required in most cases",
            "DPIA mandatory",
            "Purpose strictly limited — no function creep",
        ],
    },
    "health": {
        "risk_level": "high",
        "extra_requirements": [
            "Health data is special category (Art. 9)",
            "Explicit consent or healthcare provision basis needed",
            "Pseudonymization strongly recommended",
            "Cross-border transfer restrictions apply",
        ],
    },
    "financial": {
        "risk_level": "high",
        "extra_requirements": [
            "Payment Services Directive 2 (PSD2) may apply",
            "Anti-Money Laundering Directive obligations",
            "Strong authentication required for access",
            "Retention periods defined by financial regulation",
        ],
    },
    "children": {
        "risk_level": "high",
        "extra_requirements": [
            "Parental consent required for under-16 (or national age, min 13)",
            "Age verification mechanism required",
            "Privacy by design especially important",
            "Data minimization strictly enforced",
        ],
    },
    "anonymous": {
        "risk_level": "minimal",
        "extra_requirements": [
            "Truly anonymous data falls outside GDPR scope",
            "Ensure anonymization is irreversible (no re-identification risk)",
            "Document anonymization methodology",
        ],
    },
}


def _json_response(handler, status_code, data):
    """Hilfsfunktion: JSON-Antwort senden."""
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Cache-Control", "public, max-age=3600")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, indent=2).encode())


class handler(BaseHTTPRequestHandler):
    """
    GET /api/compliance?action=automated_decision&jurisdiction=EU
    GET /api/compliance?action=credit_scoring&jurisdiction=EU
    GET /api/compliance?action=data_processing&data_type=personal
    """

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        action = query.get("action", [""])[0].lower().strip()
        jurisdiction = query.get("jurisdiction", ["EU"])[0].upper().strip()
        data_type = query.get("data_type", [""])[0].lower().strip()

        # Parameter-Validierung
        if not action:
            _json_response(self, 400, {
                "error": "Parameter 'action' ist erforderlich",
                "usage": "/api/compliance?action=automated_decision&jurisdiction=EU",
                "available_actions": sorted(ACTION_REGISTRY.keys()),
                "available_data_types": sorted(DATA_TYPE_RULES.keys()),
            })
            return

        # Aktion nachschlagen
        action_data = ACTION_REGISTRY.get(action)
        if not action_data:
            _json_response(self, 404, {
                "error": f"Unbekannte Aktion: '{action}'",
                "available_actions": sorted(ACTION_REGISTRY.keys()),
                "hint": "Verwende einen der verfuegbaren Aktionstypen",
            })
            return

        # Basis-Antwort aufbauen
        risk_level = action_data["risk_level"]
        requirements = list(action_data["requirements"])
        recommendations = list(action_data["recommendations"])
        regulations = list(action_data["regulations"])

        # Datentyp-spezifische Regeln hinzufuegen
        if data_type and data_type in DATA_TYPE_RULES:
            dt_rules = DATA_TYPE_RULES[data_type]
            # Risikostufe anpassen falls Datentyp hoeher
            risk_order = {"minimal": 0, "limited": 1, "high": 2, "unacceptable": 3}
            if risk_order.get(dt_rules["risk_level"], 0) > risk_order.get(risk_level, 0):
                risk_level = dt_rules["risk_level"]
            requirements.extend(dt_rules["extra_requirements"])

        # Jurisdiktions-Hinweis
        jurisdiction_note = None
        if jurisdiction != "EU":
            jurisdiction_note = (
                f"Hinweis: Diese Analyse basiert auf EU-Regulierung (AI Act + GDPR). "
                f"Fuer '{jurisdiction}' gelten moeglicherweise andere Regelungen. "
                f"EU-Standards gelten als globaler Benchmark und koennen als Orientierung dienen."
            )

        response_data = {
            "action": action,
            "jurisdiction": jurisdiction,
            "risk_level": risk_level,
            "allowed": action_data["allowed"],
            "regulations": regulations,
            "requirements": requirements,
            "recommendations": recommendations,
            "gdpr_articles": action_data.get("gdpr_articles", []),
            "ai_act_category": action_data.get("ai_act_category", ""),
            "compliance_deadline": action_data.get("deadline"),
            "ai_act_timeline": AI_ACT_TIMELINE,
        }

        if data_type:
            response_data["data_type"] = data_type
            if data_type in DATA_TYPE_RULES:
                response_data["data_type_risk"] = DATA_TYPE_RULES[data_type]["risk_level"]

        if jurisdiction_note:
            response_data["jurisdiction_note"] = jurisdiction_note

        _json_response(self, 200, response_data)
