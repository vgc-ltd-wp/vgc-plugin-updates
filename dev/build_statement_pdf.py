# -*- coding: utf-8 -*-
"""Build the stakeholder statement PDF."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

OUT = r"C:\Users\Vasil Georgiev\Documents\Claude\Claude-Platform-WordPress-Recommendation.pdf"

NAVY = colors.HexColor("#1d3557")
ACCENT = colors.HexColor("#2271b1")
LIGHT = colors.HexColor("#f2f5f9")
GREY = colors.HexColor("#5a6472")

styles = getSampleStyleSheet()

h_title = ParagraphStyle("hTitle", parent=styles["Title"], fontName="Helvetica-Bold",
                         fontSize=20, leading=24, textColor=NAVY, spaceAfter=4)
h_sub = ParagraphStyle("hSub", parent=styles["Normal"], fontName="Helvetica-Oblique",
                       fontSize=10.5, textColor=GREY, spaceAfter=14)
h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                    fontSize=13, leading=16, textColor=ACCENT, spaceBefore=14, spaceAfter=6)
body = ParagraphStyle("body", parent=styles["Normal"], fontName="Helvetica",
                      fontSize=10.5, leading=15, textColor=colors.HexColor("#222222"),
                      spaceAfter=8, alignment=TA_LEFT)
point = ParagraphStyle("point", parent=body, spaceAfter=9)
small = ParagraphStyle("small", parent=body, fontSize=9.5, leading=13, textColor=GREY)
note = ParagraphStyle("note", parent=body, fontSize=9.5, leading=13, textColor=NAVY,
                      leftIndent=8, borderPadding=0)
cell = ParagraphStyle("cell", parent=body, fontSize=9.5, leading=12, spaceAfter=0)
cellb = ParagraphStyle("cellb", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)

story = []

story.append(Paragraph("Recommendation: Build the WordPress&ndash;Claude Integration on the Claude Developer Platform", h_title))
story.append(Spacer(1, 10))
story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#d6dde6"), spaceAfter=12))

story.append(Paragraph("Summary", h2))
story.append(Paragraph(
    "For long-term, production use of Claude to manage and edit our WordPress site, we recommend building on the "
    "<b>Claude Developer Platform</b> (the Anthropic API / SDK with managed API-key authentication) rather than relying on "
    "the consumer Claude applications (Desktop / web chat) and their MCP &ldquo;connector&rdquo; feature. The Platform approach is "
    "materially more <b>stable, secure, auditable, cost-transparent, and maintainable</b> for an asset the business depends on.",
    body))

story.append(Paragraph("Why the Platform is the right long-term foundation", h2))

pts = [
    ("1. Reliability and stability.",
     "A Platform integration communicates over stable, documented, versioned API contracts and the WordPress REST API. "
     "It is stateless and deterministic &mdash; no per-conversation connector to toggle, no background bridge process, no interactive "
     "session that can silently drop. Our hands-on testing of the consumer connector path surfaced repeated, time-consuming "
     "disconnections and authorization failures that are unacceptable for production; the Platform path removes that class of fragility."),
    ("2. Security and governance.",
     "The Platform uses centrally managed API keys alongside scoped, revocable WordPress credentials (Application Passwords / "
     "service accounts). Access is least-privilege, auditable, and instantly rotatable without disrupting unrelated systems. "
     "Credentials are owned and managed by us, not embedded in a consumer chat session."),
    ("3. Automation and repeatability.",
     "Platform integrations can be scripted, scheduled, version-controlled, and run unattended &mdash; bulk content operations, "
     "scheduled publishing, template/style rollouts, and CI/CD-driven changes. The consumer chat experience is interactive-only "
     "and cannot be reliably automated or reproduced."),
    ("4. Maturity and longevity.",
     "The Platform&rsquo;s APIs (Messages, tool use, official SDKs) are documented, stable, and production-grade. The consumer "
     "&ldquo;remote connector / OAuth&rdquo; path is comparatively new; in our testing the authorization flow did not reliably complete on "
     "the client side &mdash; a dependency on a maturing feature outside our control. Building on the Platform insulates us from that uncertainty."),
    ("5. Cost transparency and control.",
     "The Platform is <b>usage-based and fully measurable</b> &mdash; we pay only for what we consume, with per-project attribution, "
     "budgets, and spend caps. Costs are actively optimizable: <b>prompt caching</b> and the <b>batch API</b> cut spend on repeatable "
     "workloads, and <b>model tiering</b> (a cheaper model for routine edits, a stronger model for complex tasks) matches cost to value. "
     "This also eliminates the hidden cost we incurred on the consumer path &mdash; operator time and wasted usage spent reconnecting and "
     "re-testing after dropped sessions. By contrast, the consumer apps are <b>fixed per-seat subscriptions</b> that scale poorly for "
     "automated, unattended, or multi-site work and offer no granular cost attribution or programmatic budget control."),
    ("6. Depth and scalability.",
     "A Platform integration can combine the WordPress REST API, WP-CLI, and (where needed) file-level access into one controlled "
     "service &mdash; covering content, media, templates, and styling end-to-end, across multiple sites and users, with centralized "
     "logging and usage visibility."),
]
for head, txt in pts:
    story.append(Paragraph("<b>%s</b> %s" % (head, txt), point))

# ---- Cost illustration ----
story.append(Paragraph("Cost illustration", h2))
story.append(Paragraph(
    "<i>Illustrative &mdash; validate against current published API rates and a short pilot.</i> Assumptions: a workhorse "
    "<b>Sonnet-class</b> model for content/template/style edits and a <b>Haiku-class</b> model for routine/bulk operations; a typical "
    "&ldquo;task&rdquo; (create or revise a page) is ~2&ndash;3 model turns totalling ~30,000 input and ~5,000 output tokens; "
    "<b>prompt caching</b> and the <b>batch API</b> enabled.", small))
story.append(Paragraph(
    "<b>Per-task cost (Sonnet-class, cached): roughly $0.10&ndash;0.20 per edit.</b> Routine tasks on Haiku-class: "
    "roughly <b>$0.02&ndash;0.04 per edit.</b>", body))

data = [
    [Paragraph("Workload", cellb), Paragraph("Tasks / month", cellb),
     Paragraph("Est. monthly (Sonnet, cached)", cellb), Paragraph("With Haiku / batch for routine", cellb)],
    [Paragraph("Light", cell), Paragraph("~50", cell), Paragraph("$5&ndash;10", cell), Paragraph("$2&ndash;5", cell)],
    [Paragraph("Moderate", cell), Paragraph("~300", cell), Paragraph("$30&ndash;60", cell), Paragraph("$15&ndash;35", cell)],
    [Paragraph("Heavy", cell), Paragraph("~1,000", cell), Paragraph("$100&ndash;200", cell), Paragraph("$40&ndash;100", cell)],
]
tbl = Table(data, colWidths=[28*mm, 28*mm, 56*mm, 56*mm])
tbl.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c9d3df")),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
]))
story.append(Spacer(1, 4))
story.append(tbl)
story.append(Spacer(1, 8))

story.append(Paragraph(
    "<b>Comparison to the consumer-app model:</b> the consumer apps are fixed per-seat subscriptions (approximately "
    "$20&ndash;30 / user / month for Pro / Team tiers, $100+ / month for higher tiers). For automated, unattended, or multi-site "
    "work that model scales poorly &mdash; you pay per human seat regardless of usage, the work cannot run unattended, and there is "
    "no per-project cost attribution or spend cap. The Platform bills only for actual consumption, attributes it per project, and "
    "can be hard-capped.", body))
story.append(Paragraph(
    "<b>Hidden-cost note:</b> the consumer-connector path also carries an unbilled cost we observed directly &mdash; operator time "
    "and wasted model usage spent reconnecting and re-testing after dropped sessions. The Platform&rsquo;s stateless, deterministic "
    "calls remove that waste.", body))
story.append(Paragraph(
    "<b>Validate with a pilot:</b> run ~20 representative edits via the Platform and measure actual tokens per task. That converts "
    "the ranges above into a firm per-edit unit cost and a precise monthly projection for our real volume.", note))

story.append(Paragraph("Recommendation", h2))
story.append(Paragraph(
    "Adopt the <b>Claude Developer Platform</b> as the foundation for our WordPress automation and management capability. Treat the "
    "consumer Claude apps as a convenience for ad-hoc, interactive tasks &mdash; not as the production integration. This positions the "
    "integration to be <b>dependable, secure, auditable, cost-efficient, and durable</b> as both Claude and our site evolve.", body))

doc = SimpleDocTemplate(OUT, pagesize=A4,
                        leftMargin=20*mm, rightMargin=20*mm, topMargin=18*mm, bottomMargin=16*mm,
                        title="Claude Developer Platform - WordPress Integration Recommendation",
                        author="VGC")
doc.build(story)
print("WROTE:", OUT)
