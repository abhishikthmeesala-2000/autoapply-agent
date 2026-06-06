import { DOMParser } from "linkedom";
import { describe, expect, it } from "vitest";

import {
  buildAutofillPlan,
  detectAutofillTargets,
  summarizeAutofillResult,
} from "./autofill";

const makeDocument = (html: string): Document =>
  new DOMParser().parseFromString(html, "text/html") as unknown as Document;

const readValue = (id: string, document: Document): string => {
  const element = document.getElementById(id) as
    | HTMLInputElement
    | HTMLTextAreaElement
    | null;
  return element?.getAttribute("value") ?? element?.value ?? "";
};

const profile = {
  profileId: "profile-1",
  fullName: "Ada Lovelace",
  email: "ada@example.com",
  phone: "+1 555 010 0100",
  location: "Remote",
  currentTitle: "Senior Backend Engineer",
  currentCompany: "Analytical Engines",
  linkedinUrl: "https://www.linkedin.com/in/ada",
  portfolioUrl: "https://ada.dev",
  githubUrl: "https://github.com/ada",
  websiteUrl: "https://ada.dev",
  workAuthorization: "Authorized to work in the United States",
  answerBank: [
    {
      key: "notice-period",
      questionText: "Notice period",
      answerText: "Two weeks",
      category: "availability",
      requiresReview: false,
    },
    {
      key: "work-authorization",
      questionText: "Work authorization",
      answerText: "Authorized to work in the United States",
      category: "eligibility",
      requiresReview: false,
    },
  ],
};

const formHtml = `
  <html>
    <body>
      <form>
        <label for="first-name">First name</label>
        <input id="first-name" name="first_name" />

        <label for="last-name">Last name</label>
        <input id="last-name" name="last_name" />

        <label for="email">Email</label>
        <input id="email" name="email" />

        <label for="phone">Phone</label>
        <input id="phone" type="tel" />

        <label for="location">Location</label>
        <input id="location" />

        <label for="title">Current title</label>
        <input id="title" />

        <label for="company">Current company</label>
        <input id="company" />

        <label for="linkedin">LinkedIn</label>
        <input id="linkedin" />

        <label for="portfolio">Portfolio</label>
        <input id="portfolio" />

        <label for="notice-period">Notice period</label>
        <input id="notice-period" />

        <label for="work-authorization">Work authorization</label>
        <input id="work-authorization" />

        <label for="salary">Salary expectation</label>
        <input id="salary" />

        <label for="cover-letter">Cover letter</label>
        <textarea id="cover-letter"></textarea>

        <button type="submit">Submit</button>
      </form>
    </body>
  </html>
`;

describe("autofill engine", () => {
  it("detects visible application fields", () => {
    const document = makeDocument(formHtml);

    expect(detectAutofillTargets(document)).toHaveLength(13);
  });

  it("fills trusted values and flags uncertain or sensitive fields for review", () => {
    const document = makeDocument(formHtml);
    const result = buildAutofillPlan(document, profile);

    expect(result.profileId).toBe(profile.profileId);
    expect(result.stopBeforeSubmit).toBe(true);
    expect(result.filledCount).toBeGreaterThan(0);
    expect(result.reviewCount).toBeGreaterThan(0);
    expect(result.decisions.find((decision) => decision.label === "First name")?.status).toBe(
      "filled",
    );
    expect(result.decisions.find((decision) => decision.label === "Last name")?.status).toBe(
      "filled",
    );
    expect(result.decisions.find((decision) => decision.label === "Notice period")?.source).toBe(
      "answer-bank",
    );
    expect(
      result.decisions.find((decision) => decision.label === "Work authorization")?.status,
    ).toBe("needs-review");
    expect(result.decisions.find((decision) => decision.label === "Salary expectation")?.status).toBe(
      "needs-review",
    );
    expect(result.decisions.find((decision) => decision.label === "Cover letter")?.status).toBe(
      "needs-review",
    );
    expect(readValue("first-name", document)).toBe("Ada");
    expect(readValue("last-name", document)).toBe("Lovelace");
    expect(readValue("email", document)).toBe("ada@example.com");
    expect(readValue("phone", document)).toBe("+1 555 010 0100");
    expect(readValue("notice-period", document)).toBe("Two weeks");
    expect(readValue("salary", document)).toBe("");
    expect(summarizeAutofillResult(result)).toContain("Final submit blocked");
  });
});
