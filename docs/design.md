# Visual Design System & UI/UX Specification (design.md)

## Project: PS-8 — Settlement Q&A Agent for Fintech Support
**Document Version:** 1.0.0  
**Status:** Approved for Implementation  
**Design Persona:** Modern Fintech Operations Console + AI Investigation Workspace  
**Core Motto:** *Precise · Calm · Intelligent · Trustworthy · Investigative*

---

## 1. Design North Star & Philosophy

The **Settlement Q&A Agent** is an operational cockpit for frontline payment support teams and payment operations analysts. Its visual identity balances the rigor and clarity of high-integrity financial operations tools (such as Stripe Dashboard, Modern Treasury, and Linear) with the intuitive contextual reasoning of modern investigative workspaces.

### 1.1 Aesthetic Pillars
* **Precise:** Information is scannable at a glance. Visual hierarchy prioritizes unambiguous financial facts, exact currency amounts, and timestamp provenance.
* **Calm:** Low visual friction. Eliminates loud gradients, saturated surfaces, bouncing elements, and gratuitous animations that induce cognitive fatigue during high-volume support shifts.
* **Intelligent:** AI capabilities are presented as an assistive, tightly bounded analysis layer rather than an omnipresent chatbot gimmick.
* **Trustworthy:** Every claim displays its data origin. The interface never hides discrepancies or pretends to have answers when datasets are silent.
* **Investigative:** Cross-system reference links, multi-hop joins, timelines, and anomaly breakdowns are visually framed as an active trace journey across payment rails.

### 1.2 Anti-Personas (What the Product is NOT)
* **NOT a Consumer Banking App:** No friendly pastel lifestyle widgets, savings goal trackers, or promotional cards.
* **NOT an ERP / SAP Interface:** No dense 50-column spreadsheets with microscopic, unpadded gray text.
* **NOT a ChatGPT Clone:** No giant blank chat window waiting for open-ended prompts.
* **NOT a Cyberpunk / Crypto Terminal:** No dark neon green/purple glowing borders, CRT scanlines, or speculative ticker animations.
* **NOT a Dribbble Showcase:** No pure-glassmorphic floating cards with unreadable contrast or multi-second entry transitions.

---

## 2. Core UX Principle: Evidence Before Interpretation

The visual hierarchy strictly reinforces the core architectural principle:
$$\text{User Query} \longrightarrow \text{Multi-System Trace} \longrightarrow \text{Reconciliation} \longrightarrow \text{Deterministic Evidence} \longrightarrow \text{AI Explanation}$$

```
┌────────────────────────────────────────────────────────────────────────┐
│                        VISUAL ATTENTION HIERARCHY                      │
├────────────────────────────────────────────────────────────────────────┤
│ 1. THE STATUS & DIAGNOSIS   (What happened? Deterministic truth)       │
│ 2. THE FINANCIAL EVIDENCE   (Gross, Fee, Net, Bank status, Ledger row) │
│ 3. THE REFERENCE CHAIN      (How systems connected: TXN → SET → UTR)   │
│ 4. THE LIFECYCLE TIMELINE   (Where did processing stop?)               │
│ 5. THE EXCEPTIONS & GAPS    (What is missing? Honest uncertainty)      │
│ 6. THE AI EXPLANATION       (Plain-English translation of above facts) │
│ 7. THE ACTIONABLE SCRIPTS   (Copyable merchant response & follow-up)   │
└────────────────────────────────────────────────────────────────────────┘
```

The AI explanation panel is styled as an **interpretive layer** that visually nests below and cites the primary evidence cards.

---

## 3. Color System & Design Tokens

The application employs a **light-first design system** built on cool, neutral slates with restrained indigo accents and authoritative semantic feedback colors.

### 3.1 Base Palette Tokens

| Token Name | Hex Code | Purpose & Semantic Role |
| :--- | :--- | :--- |
| `color.background` | `#F7F8FA` | Main viewport canvas. A clean, cool off-white that reduces eye strain compared to harsh `#FFFFFF`. |
| `color.surface` | `#FFFFFF` | Primary card background, active modals, and elevated containers. |
| `color.surface.muted` | `#F1F3F6` | Secondary card fills, table header rows, timeline tracks, and code pill backgrounds. |
| `color.text.primary` | `#172033` | Deep navy-slate for primary titles, monetary values, and active table cells (WCAG AAA contrast: $> 12:1$). |
| `color.text.secondary`| `#667085` | Medium slate for field labels, timeline timestamps, and secondary captions ($> 4.8:1$). |
| `color.text.muted` | `#98A2B3` | Light slate for placeholder text, deactivated icons, and disabled states. |
| `color.border` | `#E4E7EC` | Subtle structural borders delineating cards, table rows, and input fields. |
| `color.border.subtle`| `#EEF0F3` | Interior dividers and subtle horizontal rules. |
| `color.primary` | `#4F46E5` | Primary brand accent (Indigo 600). Used for search CTAs, active tab indicators, and key focus rings. |
| `color.primary.dark`| `#3730A3` | Primary hover and active button state (Indigo 800). |
| `color.ai.tint` | `#EEF2FF` | Subtle background tint for AI-generated insight panels and follow-up chips (Indigo 50). |
| `color.ai.border` | `#C7D2FE` | Distinctive border for AI explanation containers (Indigo 200). |

---

## 4. Semantic Status Color Tokens

Every settlement diagnosis and system status maps to an explicit semantic token set consisting of a **Text Color**, **Background Tint**, and **Border Stroke**.

| Settlement State | Color Family | Text Token | Background Token | Border Token | Visual Icon |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `SUCCESSFULLY_SETTLED` | Emerald Green | `#16A34A` | `#F0FDF4` | `#BBF7D0` | `CheckCircle2` |
| `SETTLEMENT_PENDING` | Amber | `#D97706` | `#FFFBEB` | `#FDE68A` | `Clock` |
| `GATEWAY_FAILED` | Rose Red | `#DC2626` | `#FEF2F2` | `#FECACA` | `XCircle` |
| `BANK_REJECTED` | Rose Red | `#DC2626` | `#FEF2F2` | `#FECACA` | `AlertOctagon` |
| `AMOUNT_MISMATCH` | Burnt Orange | `#EA580C` | `#FFF7ED` | `#FED7AA` | `Scale` |
| `MISSING_BANK_RECORD` | Tech Blue | `#2563EB` | `#EFF6FF` | `#BFDBFE` | `HelpCircle` |
| `MISSING_LEDGER_RECORD`| Tech Blue | `#2563EB` | `#EFF6FF` | `#BFDBFE` | `FileQuestion`|
| `REFERENCE_MISMATCH` | Amber / Orange| `#D97706` | `#FFFBEB` | `#FDE68A` | `GitFork` |
| `DUPLICATE_RECORD` | Crimson Red | `#BE123C` | `#FFF1F2` | `#FECDD3` | `CopyAlert` |
| `CONFLICTING_EVIDENCE`| Deep Violet | `#7E22CE` | `#FAF5FF` | `#E9D5FF` | `AlertTriangle`|
| `INSUFFICIENT_EVIDENCE`| Slate Gray | `#4B5563` | `#F3F4F6` | `#E5E7EB` | `ShieldAlert` |

### 4.1 Accessibility Rule for Status Indicators
Color must **NEVER** be the sole vector of meaning. Every status manifestation must combine:
$$\text{Status Representation} = \text{Distinct Lucide Icon} + \text{Controlled Text Label} + \text{Semantic Color Pair} + \text{Accessible Tooltip}$$

*Incorrect:* `●` (A lonely red dot).  
*Correct:* `[ 🛑 BANK_REJECTED ] - Beneficiary account inactive` with tooltip explaining reason.

---

## 5. Typography & Numerical Hierarchy

The typography system pairs **Inter** for clean UI readability with **JetBrains Mono** for financial references, technical IDs, and timestamps.

### 5.1 Typefaces & Weights
* **Primary Sans:** `Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
  * Weights: `400 (Regular)`, `500 (Medium)`, `600 (Semibold)`, `700 (Bold)`
* **Technical Monospace:** `"JetBrains Mono", "SF Mono", Menlo, Consolas, monospace`
  * Weights: `400 (Regular)`, `500 (Medium)`

### 5.2 Type Scale Specification

| Style Category | Size | Line Height | Weight | Font Family | Example Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Page Title** | `28px` (`1.75rem`) | `36px` | `700` | Inter | Workspace header, screen title |
| **Section Heading** | `18px` (`1.125rem`)| `24px` | `600` | Inter | Section headers ("Evidence Trace") |
| **Large Financial**| `24px` (`1.5rem`) | `32px` | `600` | Inter | Gross amounts, Net payouts (`₹5,000.00`) |
| **Card Heading** | `15px` (`0.9375rem`)| `20px` | `600` | Inter | System inspector headers ("Payment Gateway")|
| **Body Primary** | `14px` (`0.875rem`)| `20px` | `400` | Inter | Internal explanations, merchant scripts |
| **Body Secondary**| `13px` (`0.8125rem`)| `18px` | `400` | Inter | Field helper text, timeline descriptions |
| **Metadata / Pill**| `12px` (`0.75rem`) | `16px` | `500` | Inter | Confidence tags, status pill badges |
| **Technical ID** | `13px` (`0.8125rem`)| `18px` | `500` | JetBrains Mono| `TXN_10482`, `SET_55012`, `UTR99281` |
| **Micro Monospace**| `11px` (`0.6875rem`)| `14px` | `400` | JetBrains Mono| ISO-8601 timestamps, raw field keys |

### 5.3 Financial Number Formatting Rules
* **Currency Symbol:** Explicit currency prefix (`₹`, `$`, `€`).
* **Decimal Precision:** Always display exactly two decimal places for fiat currency (`₹4,850.00`, never `₹4850` or `₹4850.0`).
* **Alignment:** Numerical comparison tables must right-align monetary figures using tabular figures (`font-variant-numeric: tabular-nums;`).
* **Variance Formatting:**
  * Positive variance: `+₹0.00` (Neutral/Green)
  * Negative break / missing money: `-₹350.00` in bold red (`#DC2626`) with a subtle red warning icon.

---

## 6. Spacing, Elevation & Surface Architecture

### 6.1 Spacing Scale (4px Base Grid)
The design system strictly adheres to an 8-point sub-grid (with 4px for micro-adjustments):

| Token | Size | Typical Placement |
| :--- | :--- | :--- |
| `spacing.1` | `4px` | Icon-to-text gap, badge internal padding |
| `spacing.2` | `8px` | Button internal vertical padding, chip spacing, tight list gaps |
| `spacing.3` | `12px` | Card internal element padding, input vertical padding |
| `spacing.4` | `16px` | Standard card internal padding, layout gutters |
| `spacing.5` | `20px` | Space between related cards within a column |
| `spacing.6` | `24px` | Major section gaps, grid gaps |
| `spacing.8` | `32px` | Top-level workspace section spacing |
| `spacing.12`| `48px` | Page container padding |

### 6.2 Border Radius System
* **Inputs & Standard Buttons:** `8px` (`rounded-lg`) — Clean, functional, modern.
* **Badges & Pill Tags:** `9999px` (`rounded-full`) — Pill style for quick status recognition.
* **Standard Cards & Inspectors:** `12px` (`rounded-xl`) — Restrained rounding, sturdy presence.
* **Large Workspace Panels & Modals:** `16px` (`rounded-2xl`) — Soft framing for major modules.

### 6.3 Shadows & Surface Elevation
The system relies primarily on **subtle border strokes (`#E4E7EC`) + background contrast**, using shadows only to signify elevation and focus:
* **Flat Card Surface:** `border: 1px solid #E4E7EC; box-shadow: none; background: #FFFFFF;`
* **Elevated Hover Card:** `border: 1px solid #D0D5DD; box-shadow: 0 1px 3px rgba(16, 24, 40, 0.06), 0 1px 2px rgba(16, 24, 40, 0.04);`
* **Dropdowns & Popovers:** `border: 1px solid #E4E7EC; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04);`
* **Active Input Focus:** `border-color: #4F46E5; box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15);`

---

## 7. Layout & Navigation Architecture

The interface utilizes a fixed-header, persistent-sidebar desktop layout optimized for high-density investigation work.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [Logo] Settlement Support Console    |  Workspace: Production Sandbox (Mock)    [ ● System Online ] [Agent]│
├─────────────────┬──────────────────────────────────────────────────────────────────────────────────────┤
│ 📂 Workspace    │ 🔍 Unified Investigation Bar                                                         │
│                 │ ┌───────────────────────────────────────────────────────────────────────┬──────────┐ │
│ ◉ Investigate   │ │ e.g. TXN_10482, ORD_90210, UTR99281, or "Why wasn't TXN_10482 settled?│ [Invest.] │ │
│ ▤ Exceptions    │ └───────────────────────────────────────────────────────────────────────┴──────────┘ │
│ ⏱ History       ├──────────────────────────────────────────────────────────────────────────────────────┤
│ ⚙ Settings      │ PRIMARY INVESTIGATION WORKSPACE                                                      │
│                 │                                                                                      │
│ ─────────────── │ [ Status Banner: SETTLEMENT_PENDING ]               [ Confidence: MEDIUM (75%) ]     │
│ Quick Demos:    │                                                                                      │
│ • TXN_10001 (OK)│ ┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐       │
│ • TXN_10482 (Pd)│ │ 💳 Payment Gateway   │   │ 🏦 Bank Clearing     │   │ 📒 Internal Ledger   │       │
│ • TXN_10025 (Mm)│ │ Captured: ₹5,000.00  │   │ Status: PENDING      │   │ Posted: ₹4,850.00    │       │
│ • TXN_10040 (Ms)│ └──────────────────────┘   └──────────────────────┘   └──────────────────────┘       │
│                 │                                                                                      │
│                 │ ┌──────────────────────────────────────────────────────────────────────────────────┐ │
│                 │ │ 🔗 Reference Chain: TXN_10482 ──► SET_55012 ──► (No Bank UTR) ──► LED_701928     │ │
│                 │ └──────────────────────────────────────────────────────────────────────────────────┘ │
│                 │                                                                                      │
│                 │ ┌────────────────────────────────────┐  ┌──────────────────────────────────────────┐ │
│                 │ │ ⏳ Lifecycle Timeline              │  │ ✦ AI Diagnostic Explanation             │ │
│                 │ │ ● 10:32:14 - Payment Initiated     │  │ Internal Summary & Merchant Script       │ │
│                 │ │ ● 10:32:17 - Captured ₹5,000.00    │  ├──────────────────────────────────────────┤ │
│                 │ │ ○ 11:30:00 - Bank Transfer Pending │  │ 💬 Follow-Up Q&A Assistant               │ │
│                 │ └────────────────────────────────────┘  └──────────────────────────────────────────┘ │
└─────────────────┴──────────────────────────────────────────────────────────────────────────────────────┘
```

### 7.1 Sidebar Navigation Specs
* **Width:** `240px` fixed.
* **Items:**
  * **Investigate (Primary default):** Single-transaction deep dive console.
  * **Exceptions Dashboard:** Macro-level batch settlement breaks table.
  * **Recent History:** Chronological list of investigated items during session.
* **Quick Demo Picker:** Bottom sidebar block with 4 one-click test cases representing canonical scenarios (Clean Settled, Delay, Mismatch, Missing Bank).

---

## 8. Screen-by-Screen UI Specifications

### 8.1 Screen 1: Home & Empty State (Prior to Query)
* **Goal:** Guide the support agent to immediately investigate or explore known batch issues without staring at a blank screen.
* **Visual Components:**
  1. **Hero Search Container:** Centered command input with search icon, clear button, and an explicit `Investigate` CTA button.
  2. **Prompt Suggestions:** Subtle interactive pills below the input:
     * `Try: "TXN_10482"`
     * `Try: "ORD_90210"`
     * `Try: "Show delayed settlements from September 3"`
  3. **Operational Health Quick-Cards:** Three lightweight metric widgets:
     * *Today's Volume:* `1,420 Transactions`
     * *Settled Rate:* `94.2%` (Green)
     * *Active Exceptions:* `18 Pending Investigation` (Amber)

---

### 8.2 Screen 2: Investigation Workspace (The Hero Screen)
The investigation screen renders dynamically once a query is executed.

#### Section A: The Diagnosis Header
* **Layout:** Full-width flex header.
* **Elements:**
  * Left: Active Identifier pill (`TXN_10482` in bold mono with copy icon) + Big Status Badge (`[ ⏳ SETTLEMENT_PENDING ]` with amber fill).
  * Right: Confidence Meter pill (`[ 🟡 Confidence: MEDIUM ]`) with sub-text: `"Evidence complete for Gateway & Ledger; Bank clearing in-flight"`.

#### Section B: The Three-Column System Evidence Inspector
* **Layout:** 3-column equal-width CSS Grid (`grid-cols-1 lg:grid-cols-3 gap-4`).
* **Column 1: Payment Gateway Card**
  * Top bar: `💳 Payment Gateway` + `● CAPTURED` badge.
  * Fields:
    * Gross Amount: `₹5,000.00` (Large financial format).
    * Fee Deducted: `₹150.00` (Secondary muted).
    * Net Expected: `₹4,850.00` (Semibold).
    * Order ID: `ORD_90210` (Mono pill).
    * Capture Timestamp: `2026-09-03 10:32:17 UTC`.
    * Batch ID: `SET_55012` (Clickable mono chip).
* **Column 2: Bank Settlement Card**
  * Top bar: `🏦 Bank Clearing` + `⏳ PENDING` badge.
  * Fields:
    * Disbursed Amount: `—` (Em dash indicating not yet cleared).
    * Bank UTR: `Not Issued` (Muted italic).
    * Settlement Date: `Pending` (Amber).
    * Clearing Failure Code: `None Reported` (Neutral).
* **Column 3: Internal Ledger Card**
  * Top bar: `📒 Internal Accounting Ledger` + `● POSTED` badge.
  * Fields:
    * Entry Type: `CREDIT` (Green text).
    * Credited Amount: `₹4,850.00` (Matches Gateway net).
    * Journal Entry ID: `LED_701928` (Mono pill).
    * Posting Timestamp: `2026-09-03 10:32:18 UTC`.
    * Account Reference: `SET_55012`.

---

### 8.3 Screen 3: The Signature Components

#### Signature Component 1: Reference Chain Visualizer
* **Purpose:** Make cross-system resolution immediately understandable to anyone inspecting the dispute.
* **Design:** Horizontal node-link diagram with solid lines for verified hops and dashed lines for missing or broken links.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ REFERENCE RESOLUTION TRACE                                                             │
│                                                                                        │
│  ┌──────────────┐         ┌──────────────┐         ┌──────────────┐         ┌──────────────┐  │
│  │ Transaction  │ ──────► │ Settlement   │ ─── - ─►│ Bank Rails   │ ──────► │ Ledger Entry │  │
│  │ TXN_10482    │         │ SET_55012    │         │ (No UTR Yet) │         │ LED_701928   │  │
│  └──────────────┘         └──────────────┘         └──────────────┘         └──────────────┘  │
│    ✓ Gateway Match          ✓ Batch Created          ⚠ In Progress            ✓ Journal Match │
└────────────────────────────────────────────────────────────────────────────────────────┘
```
* **Visual Styling:**
  * Verified Node: White card, `#E4E7EC` border, green checkmark icon.
  * In-Flight / Missing Node: Amber dashed border (`border-dashed border-amber-300`), warning icon.
  * Connecting Arrows: `#CBD5E1` with animated pulse dot during query processing.

#### Signature Component 2: Chronological Lifecycle Timeline
* **Purpose:** Answers *"Where exactly did this stop?"*.
* **Design:** Vertical line stepper with circular node status dots.
  * Green node (`Check`): Completed lifecycle step.
  * Amber pulsing node (`Clock`): Current active in-flight step.
  * Red node (`X`): Point of failure or rejection.
  * Gray hollow node: Future unreached steps.

```text
● 10:32:14 UTC  Payment Initiated via Web Checkout           [ Gateway ]
│
● 10:32:17 UTC  Payment Successfully Captured (₹5,000.00)     [ Gateway ]
│
● 10:32:18 UTC  Internal Ledger Balance Credited (₹4,850.00)  [ Ledger  ]
│
● 11:00:00 UTC  Consolidated into Payout Batch SET_55012      [ Gateway ]
│
○ 11:30:00 UTC  Payout File Dispatched to Clearing Bank       [ Bank    ]
│
⏹ CURRENT       Awaiting Banking Rail Confirmation & UTR      [ Bank    ]
```

---

### 8.4 Screen 4: AI Diagnostic Explanation & Support Communications

#### The AI Explanation Card
* **Container Styling:** Distinctive subtle background (`#F8FAFC`), indigo border (`#C7D2FE`), and a small sparkles header tag (`✦ AI Explanation Layer`).
* **Tabs / Sections:**
  1. **Internal Diagnostic Summary:**
     * Formatted in clean paragraphs. Highlights exact monetary numbers and state verifications in bold.
     * Epistemic breakdown bullets:
       * `✓ Known:` Payment captured; ₹150 fee deducted; Ledger entry posted.
       * `⚠ Unknown:` Bank clearing completion time; Bank UTR generation.
  2. **Merchant-Ready Response (The Support Agent's Copy Deck):**
     * Pre-formatted message card with a light green left border accent.
     * Prominent copy button in top right (`[ 📋 Copy Merchant Response ]`).
     * On click: Button turns green with checkmark (`✓ Copied to Clipboard`) for 2 seconds.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ ✦ AI Diagnostic Explanation                                  [ Verified Against Data ]│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Internal Support Summary:                                                              │
│ Payment TXN_10482 was successfully captured at 10:32:17 UTC for ₹5,000.00 with ₹150.00 │
│ processing fee. Internal ledger reflects net credit of ₹4,850.00 in batch SET_55012.   │
│ Bank nodal file reports batch status as PENDING without failure codes. Expected        │
│ turnaround is within standard 24h clearing cycle.                                      │
│                                                                                        │
│ 📋 Customer-Safe Response:                                              [ 📋 Copy ]    │
│ ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│ │ "Hello! Your payment of ₹5,000.00 was successfully processed. The net settlement   │ │
│ │  of ₹4,850.00 (after standard platform fees) is currently undergoing standard bank │ │
│ │  clearing. Bank reference numbers (UTRs) are generated once clearing completes.    │ │
│ │  Funds will reflect in your account following the next banking cycle."             │ │
│ └────────────────────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Follow-Up Q&A Assistant Bar
* Located immediately underneath the explanation.
* Displays 3 contextual suggestion chips:
  * `[ Was the customer charged twice? ]`
  * `[ What exact fee was deducted? ]`
  * `[ What is the bank failure code? ]`
* Includes an inline prompt input for custom questions: `[ Ask a follow-up question about TXN_10482... ]`.
* Answers render inline in an expandable conversational thread.

---

### 8.5 Screen 5: Exception Overview Dashboard (Batch View)
* **Goal:** High-level operational triage for managers and analysts investigating batch drops.
* **Key Components:**
  * **Top Summary KPIs:**
    * Total Investigated: `500`
    * Successfully Settled: `442` (`88.4%` - Green)
    * In-Flight Pending: `31` (`6.2%` - Amber)
    * Amount Breaks: `12` (`2.4%` - Orange)
    * Bank Rejections: `7` (`1.4%` - Red)
    * Missing Records: `8` (`1.6%` - Blue)
  * **Interactive Filter Table:**
    * Columns: `Transaction ID`, `Order ID`, `Discrepancy Type`, `Gateway Net`, `Bank Disbursed`, `Variance`, `Action`.
    * Row click action: Instantly loads that transaction into the primary Investigation Workspace.

---

## 9. Loading, Empty, and Error States

### 9.1 Multi-Stage Progress Loading Experience
When an investigation query is submitted, the UI must **NEVER** display a generic, blank spinner alone. It must render an active, deterministic progress sequence that reassures the user that multi-system correlation is underway:

```text
┌──────────────────────────────────────────────────────────────┐
│  Investigating Transaction TXN_10482...                      │
│                                                              │
│  [==========================>              ] 60%             │
│                                                              │
│  ✓ Step 1: Querying Payment Gateway logs...        (12ms)    │
│  ✓ Step 2: Traversing Reference Chain to Bank...   (18ms)    │
│  ● Step 3: Auditing Internal Ledger credit...      (In Prog) │
│  ○ Step 4: Reconciling amounts and fee math...               │
│  ○ Step 5: Synthesizing AI explanation...                    │
└──────────────────────────────────────────────────────────────┘
```

### 9.2 Error State Design Patterns
1. **Transaction Not Found (404):**
   * Visual: Illustration of an empty folder with search glass.
   * Headline: `"Transaction Identifier Not Found"`.
   * Body: `"We searched Gateway, Bank, and Ledger files but found no record matching 'TXN_99999'. Please verify the identifier."`.
   * Action: 3 quick-links to valid test transactions in the dataset.
2. **AI Service Unavailable (Graceful Fallback Mode):**
   * Visual: Subtle banner above explanation: `[ ⚠ AI Explanation Layer Offline - Showing Deterministic Findings ]`.
   * The UI cleanly renders all cards, tables, and timelines from the deterministic engine without breaking.

---

## 10. Responsive Design Specifications

While the desktop console is the primary target for operations desks, the layout adapts fluidly across viewports:

| Viewport | Breakpoint | Layout Adaptations |
| :--- | :--- | :--- |
| **Desktop** | $\ge 1280\text{px}$ | Persistent 240px sidebar; 3-column system inspector cards; side-by-side timeline and AI explanation. |
| **Laptop** | $1024\text{px} - 1279\text{px}$| Collapsed 64px icon-only sidebar; 3-column cards with condensed padding. |
| **Tablet** | $768\text{px} - 1023\text{px}$ | Hidden sidebar (hamburger drawer); system cards collapse to 2-column or stacked vertical cards. |
| **Mobile** | $< 768\text{px}$ | Stacked linear hierarchy: Search $\rightarrow$ Status Banner $\rightarrow$ Vertical System Cards $\rightarrow$ Timeline $\rightarrow$ AI Explanation. |

---

## 11. Iconography System (Lucide React)

All icons are sourced from `lucide-react` with uniform `strokeWidth={1.75}`:

| Icon Name | Context & Semantics |
| :--- | :--- |
| `Search` | Investigation search bar input icon |
| `CheckCircle2` | `SUCCESSFULLY_SETTLED` status; verified math check |
| `Clock` | `SETTLEMENT_PENDING` status; awaiting bank transfer |
| `XCircle` | `GATEWAY_FAILED` status; transaction drop |
| `AlertOctagon` | `BANK_REJECTED` status; explicit bank return |
| `Scale` | `AMOUNT_MISMATCH` discrepancy |
| `GitFork` | Reference chain hop; `REFERENCE_MISMATCH` |
| `FileQuestion` | `MISSING_LEDGER_RECORD` |
| `HelpCircle` | `MISSING_BANK_RECORD` |
| `Sparkles` | AI Explanation header badge |
| `Copy` / `Check` | Copy button before / after clicking |
| `ArrowRight` | Flow indicators in reference chains |
| `ShieldAlert` | `INSUFFICIENT_EVIDENCE` / Epistemic unknown |

---

## 12. Animation & Micro-Interactions

### 12.1 Micro-Interaction Philosophy
> **Fast, subtle, and purposeful.** Animation is used solely to signal state transitions and direct visual focus—never for decoration.

* **Durations:**
  * Micro (Buttons, badges, focus rings): `150ms ease-out`
  * Modal/Popover Reveal: `200ms cubic-bezier(0.16, 1, 0.3, 1)`
  * Card Fade-in on Search: `250ms ease-out`
* **Copy Button Feedback:** Smooth morph from `Copy` icon to green `Check` icon for exactly `2000ms`, then reverting.
* **Prohibited Animations:** Continuous spinning badges (except during active network calls), bouncing buttons, full-page screen wipe transitions.

---

## 13. Visual Design Anti-Patterns (Strictly Prohibited)

1. **No Neon / Cyberpunk Accents:** Avoid dark purple/cyan glows or futuristic HUD styling.
2. **No Unanchored Floating Chatbots:** Do NOT place a floating circular chat bubble in the bottom right corner. Q&A must live inside the active investigation context.
3. **No Decorative Charts:** Do not show meaningless area graphs (e.g., fake CPU spikes or generic sine waves) to fill white space.
4. **No Unformatted Financial Strings:** Never output raw numbers like `4850.5`—always format as `₹4,850.50`.
5. **No Wall of Text:** AI explanations must be structured into short, punchy paragraphs with clear bolding and bulleted fact lists.
6. **No Ambiguous Status Colors:** Never use yellow for success or blue for a critical financial failure.

---

## 14. Design Acceptance Checklist

```markdown
## Design Acceptance Checklist

- [x] Light-first visual system defined
- [x] Color tokens defined (#F7F8FA background, #FFFFFF surface, #172033 text)
- [x] Semantic status colors defined for all 11 settlement states
- [x] Accessibility rules defined (Icon + Text + Color + Tooltip)
- [x] Inter typography defined with clear weight hierarchy
- [x] Monospace identifier typography defined (JetBrains Mono)
- [x] Financial number hierarchy and tabular alignment defined
- [x] Spacing system defined (4px / 8px grid)
- [x] Radius system defined (8px inputs/buttons, 12px cards, 16px panels)
- [x] Shadow/border system defined (subtle border-first elevation)
- [x] Navigation structure defined (Investigate, Exceptions, History)
- [x] Overview / Home screen defined with helpful quick-starts
- [x] Investigation screen defined as the core operational cockpit
- [x] Three-column evidence cards defined (Gateway, Bank, Ledger)
- [x] Reference chain signature component defined (TXN → SET → UTR → LED)
- [x] Investigation timeline signature component defined
- [x] Exception and epistemic honesty UX defined (Known vs Unknown)
- [x] Confidence UX defined (Rule-based, explainable, HIGH/MED/LOW)
- [x] AI explanation UX defined with distinctive subtle indigo framing
- [x] Support response UX defined with one-click copy feedback
- [x] Follow-up Q&A UX defined with contextual chips
- [x] History UX defined with compact scannable rows
- [x] Exception dashboard defined for macro batch triage
- [x] Loading experience defined with multi-step deterministic progress
- [x] Error states defined with constructive recovery suggestions
- [x] Empty states defined with actionable starting queries
- [x] Responsive behavior defined across Desktop, Tablet, and Mobile
- [x] Animation rules defined (subtle, fast, purposeful)
- [x] Dark mode direction defined as future-compatible extension
- [x] Component language catalog defined
- [x] Design anti-patterns explicitly prohibited
- [x] Design tokens categorized and mapped
- [x] No unnecessary UI dependencies introduced (pure Tailwind + Lucide)
```

---

> **Implementation Note:** This document has also been saved to disk at [`design.md`](file:///C:/Users/HP/.gemini/antigravity/scratch/settlement-qa-agent/design.md) in the project workspace directory `C:\Users\HP\.gemini\antigravity\scratch\settlement-qa-agent` alongside [`prd.md`](file:///C:/Users/HP/.gemini/antigravity/scratch/settlement-qa-agent/prd.md) and [`arch.md`](file:///C:/Users/HP/.gemini/antigravity/scratch/settlement-qa-agent/arch.md) to serve as the visual specification for frontend implementation.
