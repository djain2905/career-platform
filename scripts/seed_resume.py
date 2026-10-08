"""Load Dhwani Jain's resume into the Career Platform database.

Source: "Dhwani Jain Resume .pdf"

Re-runnable: wipes the existing profile and its dependent rows, then reloads.
Dates are month-precision from the resume and stored as the first of the month.

Usage:  python -m scripts.seed_resume
"""
from __future__ import annotations

from app.db import connect, init_schema

PROFILE = {
    "full_name": "Dhwani Jain",
    # Derived from the education + current-role lines; the resume has no
    # headline or summary section of its own.
    "headline": "Information Systems & Business Analytics student at Loyola Marymount University",
    "summary": None,
    "location": "Los Angeles, CA",
    "pronouns": None,
    "preferred_role": None,
    "availability_status": None,
}

CONTACTS = [
    ("email", "Email", "dhwanijain2905@gmail.com", "mailto:dhwanijain2905@gmail.com", 1),
    ("phone", "Phone", "+1 (323) 532-5205", "tel:+13235325205", 0),
    ("linkedin", "LinkedIn", "linkedin.com/in/dhwani-jain2", "https://www.linkedin.com/in/dhwani-jain2", 0),
    ("github", "GitHub", "github.com/djain2905", "https://github.com/djain2905", 0),
]

EDUCATION = [
    {
        "institution": "Loyola Marymount University (LMU)",
        "degree": "Bachelor of Science",
        "field_of_study": "Information Systems and Business Analytics, minor in Computer Science",
        "location": "Los Angeles, CA",
        "start_date": None,
        "end_date": "2027-05-01",
        "is_expected": 1,
        "description": (
            "Coursework: Network Cloud Computing, Systems Analysis Design, "
            "Computer Systems Organization, Data Structures and Applications, "
            "Database Management Systems, Developing Business Applications using SQL, "
            "Computer Programming, Computer Graphics"
        ),
    },
    {
        "institution": "Universal American School, Dubai",
        "degree": "International Baccalaureate Diploma",
        "field_of_study": None,
        "location": "Dubai, U.A.E.",
        "start_date": None,
        "end_date": "2023-05-01",
        "is_expected": 0,
        "description": None,
    },
]

EXPERIENCE = [
    {
        "company_name": "HUM Nutrition",
        "role_title": "Data Analyst Intern",
        "employment_type": "Internship",
        "location": "Los Angeles, CA",
        "start_date": "2026-06-01",
        "end_date": None,
        "is_current": 1,
        "highlights": [
            "Delivered a data-driven commercial growth strategy to client leadership, analyzing 3+ years of HUM Nutrition's Target Corp sales and consumer demand to uncover GLP-1's rise to 56% of monthly sales.",
            "Evaluated growth through analysis of sales patterns, finding select promotions that drove sales to a 33% lift - informing marketing decisions.",
            "Automated HUM Nutrition's weekly ULTA Beauty sales reporting into a self-updating omnichannel dashboard (Google Apps Script, Excel) - tracking sell-through, inventory, and forecasting across SKUs, in-store, and e-commerce - cutting 3 hours/week of manual work.",
            "Backfilled and validated 25 weeks of SKU and channel-level ULTA sales data and built pace-to-plan forecasting against an annual sales goal.",
        ],
    },
    {
        "company_name": "DecisionNext",
        "role_title": "Data Analytics Engineer Intern",
        "employment_type": "Internship",
        "location": "San Francisco, CA",
        "start_date": "2026-06-01",
        "end_date": "2026-08-01",
        "is_current": 0,
        "highlights": [
            "Built 24+ automated ETL pipelines in Python ingesting trade, water, and satellite data from 15+ sources across REST APIs, web scraping, and PDF parsing - standardizing all outputs into a self-archiving schema.",
            "Led a regression analysis to identify the drivers of Australian rice supply, testing 6 variables across 8 months against two targets using correlation analysis, multi-model OLS regression, and year-over-year detrending.",
            "Synthesized findings into a stakeholder presentation proposing a forecasting approach to close the benchmark model's 50%+ error.",
        ],
    },
    {
        "company_name": "Scorpio Tankers",
        "role_title": "Business Analyst Intern",
        "employment_type": "Internship",
        "location": "Greenwich, CT",
        "start_date": "2025-06-01",
        "end_date": "2025-08-01",
        "is_current": 0,
        "highlights": [
            "Delivered LNG bunkering vessel investment pitch, leveraging maritime datasets and scenario-based financial models to support strategic capital allocation; presented recommendations to 30+ stakeholders.",
            "Built a predictive risk model using Prophet to forecast vessel incidents; authored a high-visibility report, flagging operational risks.",
            "Performed on-site fieldwork aboard STI Modest, observing vessel operations and leveraging firsthand data to strengthen model outputs.",
        ],
    },
    {
        "company_name": "Digital Veterans Legacy Project",
        "role_title": "Student Research Assistant",
        "employment_type": "Part-time",
        "location": "Los Angeles, CA",
        "start_date": "2025-01-01",
        "end_date": "2026-08-01",
        "is_current": 0,
        "highlights": [
            "Leading research on biographical information for Veterans Interred at Los Angeles National Cemetery.",
            "Curating biographies that are uploaded to Veterans Legacy Memorial Website.",
            "Presented research at LMU's Undergraduate Research Symposium, showcasing findings to the broader research community.",
        ],
    },
    {
        "company_name": "GeoServe Energy Transport DMCC",
        "role_title": "Product Development Intern",
        "employment_type": "Internship",
        "location": "Dubai, U.A.E.",
        "start_date": "2024-06-01",
        "end_date": "2024-07-01",
        "is_current": 0,
        "highlights": [
            'Completed the "Building a Database Agent" course on DeepLearning.AI, enhancing data sorting and analysis capabilities.',
            "Leveraged PowerBI for validating UAT data within operations dashboards and performed detailed KPI analysis for bunker sales.",
            "Conducted SEO analysis for Geoserve's verticals and competitors to increase online visibility.",
        ],
    },
]

PROJECTS = [
    {
        "title": "L'Oréal Consumer Intelligence Dashboard - Lancôme Whitespace Analysis",
        "slug": "loreal-consumer-intelligence",
        "short_description": "End-to-end Consumer & Market Insights pipeline and Streamlit dashboard surfacing product whitespace for Lancôme from 600,000+ Sephora reviews.",
        "repo_url": "https://github.com/djain2905/loreal-consumer-intelligence",
        "external_url": None,
        "featured": 1,
        "start_date": None,
        "end_date": None,
        "highlights": [
            "Built an end-to-end Consumer & Market Insights (CMI) pipeline; deployed Streamlit dashboard to identify product whitespace opportunities for Lancôme from over 600,000 Sephora reviews.",
            "Detected and classified consumer desire/need language across 5,951 Lancôme specific reviews into 9 consumer need themes using SQL and regex.",
            "Automated weekly data pipelines via GitHub Actions and built an LLM-queryable brand knowledge base from 19 scraped sources.",
        ],
    },
    {
        "title": "LMU Datathon - 1st Place Winner",
        "slug": "lmu-datathon",
        "short_description": "First place out of 150+ participants from 18+ universities, analyzing the impact of meal break regulations on EMT operations.",
        "repo_url": None,
        "external_url": None,
        "featured": 1,
        "start_date": None,
        "end_date": None,
        "highlights": [
            "Competed against 150+ participants from 18+ universities.",
            "Analyzed the impact of meal break regulations on EMT operations using Python, SQL, and Excel; presented findings to 10+ industry judges.",
        ],
    },
    {
        "title": "Auto Recall Risk & Stock Impact Analysis",
        "slug": "auto-recall-risk-stock-impact",
        "short_description": "Finalist at Manhattan University's Business Analytics Competition 2026; NLP severity classifier and event-study model linking vehicle recalls to abnormal stock returns.",
        "repo_url": None,
        "external_url": None,
        "featured": 0,
        "start_date": None,
        "end_date": "2026-01-01",
        "highlights": [
            "Competed against 100+ participants from 21+ universities nationwide.",
            "Analyzed 18,000+ NHTSA vehicle recalls records (2000-2025); built an NLP severity classifier and event-study model linking recall intensity to abnormal stock returns across 15+ global OEMs.",
            "Presented real-time investment signals and a back tested buy/avoid framework under live new-data conditions to industry judges.",
        ],
    },
]

# (name, category, proficiency_level)
SKILLS = [
    ("Microsoft Excel", "Technical", None),
    ("Microsoft Access", "Technical", None),
    ("PowerBI", "Technical", None),
    ("Python", "Technical", None),
    ("Prophet", "Technical", None),
    ("pandas", "Technical", None),
    ("SQL", "Technical", None),
    ("Java", "Technical", None),
    ("JSON", "Technical", None),
    ("Snowflake", "Technical", None),
    ("Streamlit", "Technical", None),
    ("dbt", "Technical", None),
    ("Docker", "Technical", None),
    ("GitHub Actions", "Technical", None),
    ("English", "Language", "Fluent"),
    ("Hindi", "Language", "Fluent"),
    ("Spanish", "Language", "Fluent"),
    ("Arabic", "Language", "Fluent"),
]

CERTIFICATIONS = [
    {
        "name": "Building a Database Agent",
        "issuer": "DeepLearning.AI",
        "date_earned": "2024-06-01",
        "credential_url": None,
    },
]

ACHIEVEMENTS = [
    {
        "title": "1st Place - LMU Datathon",
        "description": "First place against 150+ participants from 18+ universities.",
        "date_earned": None,
        "source": "LMU Datathon",
    },
    {
        "title": "Finalist - Manhattan University Business Analytics Competition 2026",
        "description": "Finalist against 100+ participants from 21+ universities nationwide.",
        "date_earned": "2026-01-01",
        "source": "Manhattan University",
    },
    {
        "title": "Presenter - LMU Undergraduate Research Symposium",
        "description": "Presented Digital Veterans Legacy Project research to the broader research community.",
        "date_earned": None,
        "source": "Loyola Marymount University",
    },
    {
        "title": "Treasurer - National Honor Society",
        "description": None,
        "date_earned": None,
        "source": "National Honor Society",
    },
    {
        "title": 'Founder - "Let\'s Talk About It"',
        "description": None,
        "date_earned": None,
        "source": None,
    },
]


def seed(conn) -> dict[str, int]:
    cur = conn.cursor()

    # Idempotent reload: drop this person and let cascades clear dependents.
    cur.execute("DELETE FROM person_profile WHERE full_name = %s", (PROFILE["full_name"],))
    cur.execute("DELETE FROM skill")

    pid = cur.execute(
        """INSERT INTO person_profile
           (full_name, headline, summary, location, pronouns,
            preferred_role, availability_status)
           VALUES (%(full_name)s, %(headline)s, %(summary)s, %(location)s, %(pronouns)s,
                   %(preferred_role)s, %(availability_status)s)
           RETURNING id""",
        PROFILE,
    ).fetchone()["id"]

    for i, (ctype, label, value, url, primary) in enumerate(CONTACTS):
        cur.execute(
            """INSERT INTO contact_method
               (profile_id, type, label, value, url, is_primary, order_index)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (pid, ctype, label, value, url, bool(primary), i),
        )

    for i, ed in enumerate(EDUCATION):
        cur.execute(
            """INSERT INTO education_record
               (profile_id, institution, degree, field_of_study, location,
                start_date, end_date, is_expected, description, order_index)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (pid, ed["institution"], ed["degree"], ed["field_of_study"],
             ed["location"], ed["start_date"], ed["end_date"],
             bool(ed["is_expected"]), ed["description"], i),
        )

    for i, job in enumerate(EXPERIENCE):
        eid = cur.execute(
            """INSERT INTO role_experience
               (profile_id, company_name, role_title, employment_type, location,
                start_date, end_date, is_current, order_index)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (pid, job["company_name"], job["role_title"], job["employment_type"],
             job["location"], job["start_date"], job["end_date"],
             bool(job["is_current"]), i),
        ).fetchone()["id"]
        for j, body in enumerate(job["highlights"]):
            cur.execute(
                "INSERT INTO experience_highlight (experience_id, body, order_index) VALUES (%s, %s, %s)",
                (eid, body, j),
            )

    for i, proj in enumerate(PROJECTS):
        prid = cur.execute(
            """INSERT INTO project
               (profile_id, title, slug, short_description, start_date, end_date,
                external_url, repo_url, featured, order_index)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (pid, proj["title"], proj["slug"], proj["short_description"],
             proj["start_date"], proj["end_date"], proj["external_url"],
             proj["repo_url"], bool(proj["featured"]), i),
        ).fetchone()["id"]
        for j, body in enumerate(proj["highlights"]):
            cur.execute(
                "INSERT INTO project_highlight (project_id, body, order_index) VALUES (%s, %s, %s)",
                (prid, body, j),
            )

    for i, (name, category, level) in enumerate(SKILLS):
        sid = cur.execute(
            "INSERT INTO skill (name, category, sort_order) VALUES (%s, %s, %s) RETURNING id",
            (name, category, i),
        ).fetchone()["id"]
        cur.execute(
            """INSERT INTO skill_proficiency (profile_id, skill_id, proficiency_level)
               VALUES (%s, %s, %s)""",
            (pid, sid, level),
        )

    for cert in CERTIFICATIONS:
        cur.execute(
            """INSERT INTO certification (profile_id, name, issuer, date_earned, credential_url)
               VALUES (%s, %s, %s, %s, %s)""",
            (pid, cert["name"], cert["issuer"], cert["date_earned"], cert["credential_url"]),
        )

    for i, ach in enumerate(ACHIEVEMENTS):
        cur.execute(
            """INSERT INTO achievement
               (profile_id, title, description, date_earned, source, order_index)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (pid, ach["title"], ach["description"], ach["date_earned"], ach["source"], i),
        )

    conn.commit()

    counts = {}
    for table in ("person_profile", "contact_method", "education_record",
                  "role_experience", "experience_highlight", "project",
                  "project_highlight", "skill", "skill_proficiency",
                  "certification", "achievement"):
        counts[table] = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
    return counts


def main() -> None:
    with connect() as conn:
        init_schema(conn)
        counts = seed(conn)
        where = f"{conn.info.host}/{conn.info.dbname}"
    print(f"Seeded {where}")
    for table, n in counts.items():
        print(f"  {table:<22} {n}")


if __name__ == "__main__":
    main()
