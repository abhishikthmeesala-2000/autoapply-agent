import { describe, expect, it } from "vitest";
import { DOMParser } from "linkedom";

import { extractJobDetails, toExtractionUiState } from "./extractor";

const greenhouseHtml = `
  <html>
    <head>
      <meta property="og:title" content="Backend Engineer">
      <meta property="og:site_name" content="Acme">
      <meta property="og:url" content="https://careers.acme.example/jobs/1">
    </head>
    <body>
      <main>
        <div class="location">Remote</div>
        <section class="job-description">
          Build APIs and services.
        </section>
      </main>
    </body>
  </html>
`;

const leverHtml = `
  <html>
    <head>
      <meta property="og:title" content="Backend Engineer">
      <meta property="og:site_name" content="Acme">
      <meta property="og:url" content="https://jobs.lever.co/acme/backend">
    </head>
    <body>
      <main>
        <div class="location">Remote</div>
        <div class="posting-description">Build services with FastAPI.</div>
      </main>
    </body>
  </html>
`;

const ashbyHtml = `
  <html>
    <head>
      <meta property="og:title" content="Backend Engineer">
      <meta property="og:site_name" content="Acme">
      <meta property="og:url" content="https://jobs.ashbyhq.com/acme/backend">
    </head>
    <body>
      <main>
        <div class="location">Remote</div>
        <div class="job-description">Python, APIs, data.</div>
      </main>
    </body>
  </html>
`;

const workdayHtml = `
  <html>
    <head>
      <meta property="og:title" content="Backend Engineer">
      <meta property="og:site_name" content="Acme">
      <meta property="og:url" content="https://workday.example/jobs/1">
    </head>
    <body>
      <main>
        <div data-automation-id="locations">Remote</div>
        <div data-automation-id="jobDescriptionText">Build enterprise workflows.</div>
      </main>
    </body>
  </html>
`;

const linkedinHtml = `
  <html>
    <head>
      <meta property="og:title" content="Backend Engineer">
      <meta property="og:site_name" content="LinkedIn">
      <meta property="og:url" content="https://www.linkedin.com/jobs/view/1">
    </head>
    <body>
      <main>
        <h1 class="topcard__title">Backend Engineer</h1>
        <div class="topcard__org-name-link">Acme</div>
        <div class="topcard__flavor--bullet">Remote</div>
        <div class="description__text">Build services for recruiters.</div>
      </main>
    </body>
  </html>
`;

const genericHtml = `
  <html>
    <head>
      <title>Platform Engineer</title>
      <meta property="og:site_name" content="Example Co">
      <meta property="og:url" content="https://careers.example.com/jobs/platform">
    </head>
    <body>
      <main>
        <p>Location: Remote</p>
        <p>Build job systems.</p>
      </main>
    </body>
  </html>
`;

const makeDocument = (html: string): Document => {
  return new DOMParser().parseFromString(html, "text/html") as unknown as Document;
};

describe("extractJobDetails", () => {
  it("extracts greenhouse jobs", () => {
    const result = extractJobDetails(
      makeDocument(greenhouseHtml),
      "https://boards-api.greenhouse.io/v1/boards/acme/jobs/1",
    );

    expect(result.job?.source).toBe("greenhouse");
    expect(result.job?.title).toBe("Backend Engineer");
    expect(result.job?.company).toBe("Acme");
    expect(result.job?.location).toBe("Remote");
    expect(result.job?.applyUrl).toContain("acme.example");
  });

  it("extracts lever jobs", () => {
    const result = extractJobDetails(
      makeDocument(leverHtml),
      "https://api.lever.co/v0/postings/acme/backend",
    );

    expect(result.job?.source).toBe("lever");
    expect(result.job?.title).toBe("Backend Engineer");
    expect(result.job?.company).toBe("Acme");
  });

  it("extracts ashby jobs", () => {
    const result = extractJobDetails(
      makeDocument(ashbyHtml),
      "https://jobs.ashbyhq.com/acme/backend",
    );

    expect(result.job?.source).toBe("ashby");
    expect(result.job?.title).toBe("Backend Engineer");
  });

  it("extracts workday jobs", () => {
    const result = extractJobDetails(
      makeDocument(workdayHtml),
      "https://workday.example/jobs/1",
    );

    expect(result.job?.source).toBe("workday");
    expect(result.job?.title).toBe("Backend Engineer");
    expect(result.job?.location).toBe("Remote");
  });

  it("extracts linkedin jobs when already open", () => {
    const result = extractJobDetails(
      makeDocument(linkedinHtml),
      "https://www.linkedin.com/jobs/view/1",
    );

    expect(result.job?.source).toBe("linkedin");
    expect(result.job?.title).toBe("Backend Engineer");
    expect(result.job?.company).toBe("Acme");
  });

  it("falls back to visible page text for generic pages", () => {
    const result = extractJobDetails(
      makeDocument(genericHtml),
      "https://careers.example.com/jobs/platform",
    );

    expect(result.job?.source).toBe("generic");
    expect(result.job?.title).toBe("Platform Engineer");
    expect(result.job?.company).toBe("Example Co");
  });

  it("marks unsupported or incomplete pages for review rather than submit", () => {
    const state = toExtractionUiState({
      job: null,
      reason: "LinkedIn page must already be open and visible for extraction.",
    });

    expect(state.status).toBe("needs-review");
    expect(state.source).toBeNull();
    expect(state.reason).toContain("LinkedIn");
  });
});
