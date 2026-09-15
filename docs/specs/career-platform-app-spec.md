# Career Platform App Specification

Status: Draft approved for design review
Date: 2026-09-15

## 1. Overview

This project is a database-driven personal resume website designed to help a professional attract employers and recruiters while remaining flexible enough to evolve into a broader career platform. The product is not a one-off portfolio site; it is a content system that turns professional profile data into a polished public-facing experience.

The system will model professional identity as structured data so the user can update experience, skills, projects, contact information, and narrative content without manually editing presentation code. This keeps the site maintainable and scalable as it grows.

## 2. Product Goal

Create a polished, recruiter-friendly career website that presents the user as a strong candidate and supports future expansion into a broader career platform.

## 3. Primary Users

### 3.1 Recruiters and employers
These users want to quickly assess fit, experience, skills, and project work. They expect clear, scannable content and strong evidence of impact.

### 3.2 Professional contacts and collaborators
These users may browse for a deeper understanding of the person’s work, domain, and professional identity.

### 3.3 Content owner / admin
This is the primary internal user who maintains the profile, updates achievements, and publishes new content.

## 4. Business Objectives

- Present a professional profile that attracts hiring attention.
- Make it easy to update the resume and portfolio without code changes.
- Show work in a way that communicates impact, not just responsibilities.
- Support future growth into a more complete career platform.

## 5. Non-Goals

The initial version will not include:
- a social network or public forum
- a full job marketplace
- multi-user accounts or company profiles
- a full ATS or internal hiring workflow
- a blog engine as a core requirement unless it becomes a natural extension of the content model

## 6. Functional Requirements

### 6.1 Public website requirements
The public site shall provide the following sections:
- home / landing page
- about / profile page
- experience timeline
- project portfolio / case studies
- skills overview
- education and credentials
- contact page

The site shall be responsive and readable on mobile and desktop.

The public site shall render content dynamically from structured records rather than static hard-coded copy only.

### 6.2 Admin requirements
The admin experience shall allow the content owner to:
- add, edit, publish, archive, and reorder work experience
- add, edit, publish, archive, and reorder project entries
- manage skills and categories
- update profile summary and professional positioning
- manage contact methods and links
- create and update education records and credentials
- manage featured content sections
- publish updates to the public site without developer assistance

### 6.3 Content lifecycle
Each core record type should support a life cycle such as:
- draft
- published
- archived

The system should allow a record to be stored without being visible publicly until the owner chooses to publish it.

## 7. Content Model

The system should use a structured, relational data model rather than embedding all content into presentation templates.

### 7.1 PersonProfile
Represents the main person being represented.

Fields may include:
- id
- full_name
- headline
- summary
- location
- pronouns
- preferred_role
- availability_status
- created_at
- updated_at

### 7.2 ContactMethod
Represents external links and contact channels.

Fields may include:
- id
- profile_id
- type
- label
- value
- url
- is_primary
- created_at

Examples:
- email
- LinkedIn
- GitHub
- personal website
- portfolio link
- social account

### 7.3 RoleExperience
Represents employment history.

Fields may include:
- id
- profile_id
- company_name
- role_title
- employment_type
- location
- start_date
- end_date
- is_current
- summary
- achievements
- order_index
- created_at
- updated_at

### 7.4 Project
Represents professional or personal projects.

Fields may include:
- id
- profile_id
- title
- slug
- short_description
- long_description
- status
- start_date
- end_date
- external_url
- repo_url
- featured
- image_url
- created_at
- updated_at

### 7.5 Skill
Represents reusable skills and capabilities.

Fields may include:
- id
- name
- category
- description
- sort_order
- created_at

### 7.6 SkillProficiency
Represents a user’s relationship to a skill.

Fields may include:
- id
- profile_id
- skill_id
- proficiency_level
- years_experience
- notes

### 7.7 EducationRecord
Represents academic background.

Fields may include:
- id
- profile_id
- institution
- degree
- field_of_study
- start_date
- end_date
- description

### 7.8 Certification
Represents credentials and certifications.

Fields may include:
- id
- profile_id
- name
- issuer
- date_earned
- credential_url

### 7.9 Achievement
Represents notable accomplishments and recognitions.

Fields may include:
- id
- profile_id
- title
- description
- date_earned
- source

### 7.10 ContentSection
Represents custom narrative blocks that do not fit a single core entity.

Fields may include:
- id
- profile_id
- section_type
- title
- body
- order_index
- is_published
- created_at
- updated_at

### 7.11 Tag and EntityTag
The system should support tags and cross-linking for future classification and filtering.

## 8. User Stories

### 8.1 Recruiter user stories
- As a recruiter, I want to quickly scan the candidate’s background so I can assess fit for a role.
- As a recruiter, I want to view projects and case studies so I can understand the candidate’s practical work.
- As a recruiter, I want to see skills and years of experience so I can compare candidates quickly.
- As a recruiter, I want contact information or a contact flow so I can reach out.

### 8.2 Admin user stories
- As the profile owner, I want to update my work history without editing code.
- As the profile owner, I want to add projects with links and proof of work.
- As the profile owner, I want to manage featured content that appears on the homepage.
- As the profile owner, I want to ensure content is published only when it is ready.

## 9. Non-Functional Requirements

### 9.1 Performance
- Public pages should load quickly and be mobile-friendly.
- Database queries should be efficient and avoid unnecessary joins on large lists.
- Media should be optimized for web delivery.

### 9.2 Security
- Admin-only authentication and authorization for editing workflows.
- Sanitization and validation of user-generated or admin-submitted content.
- Protection against malformed URLs and invalid dates.

### 9.3 Accessibility
- The public site should be accessible to keyboard and screen-reader users.
- Semantic HTML and clear visual hierarchy should be used.
- Contrast and readability should meet modern accessibility standards.

### 9.4 SEO
- Each public page should have proper title and meta description.
- Structured content should be crawlable and semantically meaningful.
- Open Graph metadata should be supported for social sharing.

## 10. System Architecture Requirements

The product should be built with a database-first architecture that separates content storage from content presentation.

### Required characteristics
- content stored in a database
- admin interface for content management
- public rendering layer for site pages
- API or server layer for data access
- ability to evolve into additional modules without redesigning the core model

### Preferred architecture direction
The preferred approach is a modern full-stack app with:
- relational database for structured content
- backend/API layer for content management and read operations
- admin dashboard for editing
- public frontend for recruiter-facing presentation

This is preferred because it provides a good balance of flexibility, maintainability, and extensibility.

## 11. Future Expansion Support

The data model must be designed so future additions can fit naturally without a total rewrite. Examples of future additions:
- blog posts / articles
- speaking engagements
- testimonials
- case study categories
- career timeline milestones
- job opportunity tracking
- newsletter signups
- content personalization or role-specific resume views

These should be supported by the same core content structure and admin philosophy.

## 12. Success Criteria

The project is successful when:
- the public site clearly communicates professional value to employers and recruiters
- the content owner can update profiles and portfolio items without developer help
- the system supports future expansion without hard-coded redesigns
- the site presents work clearly, consistently, and with strong SEO and mobile usability

## 13. Acceptance Criteria

### Public site
- The site includes a professional summary, employment history, skills, projects, and contact methods.
- Page content is readable, responsive, and recruiter-friendly.
- The site has clear navigation and strong readability.

### Admin workflow
- The content owner can create and update profile data through a structured admin interface.
- Content can be published and archived without code changes.
- Records appear on the website after publishing.

### Data model
- Core entities are stored as structured records in a database.
- Future modules can be added without replacing the core schema.
- Content is separated from presentation.

## 14. Out of Scope for v1

The following items are not required in the first version:
- advanced analytics dashboards beyond basic page tracking
- complex recommendation engine
- multi-tenant architecture
- payments or subscriptions
- large-scale networking features
- ATS integrations

## 15. Open Decisions to Resolve Before Implementation

The following design decisions are intentionally deferred until implementation planning:
- exact frontend framework
- exact backend stack
- exact database choice and ORM
- static vs server-rendered public pages
- deployment topology
- contact form implementation details

These are implementation-level decisions and are not part of this product specification.
