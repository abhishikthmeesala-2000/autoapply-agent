export type SupportedJobSource =
  | "greenhouse"
  | "lever"
  | "ashby"
  | "workday"
  | "linkedin"
  | "generic";

export interface ExtractedJobDetails {
  source: SupportedJobSource;
  title: string;
  company: string;
  location: string | null;
  description: string;
  applyUrl: string;
  url: string;
}

export interface ExtractionResult {
  job: ExtractedJobDetails | null;
  reason?: string;
}

export interface ExtractionUiState {
  source: SupportedJobSource | null;
  title: string;
  company: string;
  location: string;
  status: "idle" | "extracted" | "needs-review";
  reason?: string;
}

const trim = (value: string | null | undefined): string => (value ?? "").trim();

const cleanText = (value: string | null | undefined): string =>
  trim(value).replace(/\s+/g, " ");

const firstMatch = (patterns: RegExp[], text: string): string | null => {
  for (const pattern of patterns) {
    const match = pattern.exec(text);
    if (match?.[1]) {
      return cleanText(match[1]);
    }
  }
  return null;
};

const metaContent = (doc: Document, selectors: string[]): string | null => {
  for (const selector of selectors) {
    const element = doc.querySelector(selector);
    const content = element?.getAttribute("content");
    if (content) {
      return cleanText(content);
    }
  }
  return null;
};

const textFromSelectors = (
  doc: Document,
  selectors: string[],
): string | null => {
  for (const selector of selectors) {
    const element = doc.querySelector(selector);
    const text = cleanText(element?.textContent);
    if (text) {
      return text;
    }
  }
  return null;
};

const bodyText = (doc: Document): string =>
  cleanText(doc.body?.innerText ?? doc.body?.textContent ?? "");

const detectSource = (url: string, doc: Document): SupportedJobSource => {
  const host = url.toLowerCase();
  if (
    host.includes("greenhouse") ||
    doc.querySelector('script[src*="greenhouse"]')
  ) {
    return "greenhouse";
  }
  if (host.includes("lever") || doc.querySelector('script[src*="lever"]')) {
    return "lever";
  }
  if (host.includes("ashby") || doc.querySelector('script[src*="ashby"]')) {
    return "ashby";
  }
  if (host.includes("workday") || doc.querySelector('script[src*="workday"]')) {
    return "workday";
  }
  if (host.includes("linkedin")) {
    return "linkedin";
  }
  return "generic";
};

const greenhouseExtract = (doc: Document, url: string): ExtractionResult => {
  const title =
    textFromSelectors(doc, ["h1"]) ||
    metaContent(doc, ['meta[property="og:title"]', 'meta[name="title"]']) ||
    null;
  const company =
    metaContent(doc, ['meta[property="og:site_name"]']) ||
    firstMatch([/\bCompany\s*[:\-]\s*([^\n|]+)/i], bodyText(doc)) ||
    null;
  const location =
    textFromSelectors(doc, [".location", "[data-qa='job-location']"]) ||
    firstMatch([/\bLocation\s*[:\-]\s*([^\n|]+)/i], bodyText(doc));
  const description =
    textFromSelectors(doc, [
      ".job-description",
      "[data-qa='job-description']",
      "main",
    ]) || bodyText(doc);
  const applyUrl = metaContent(doc, ['meta[property="og:url"]']) || url;

  if (!title || !company || !description) {
    return {
      job: null,
      reason: "Unable to extract complete Greenhouse job data.",
    };
  }

  return {
    job: {
      source: "greenhouse",
      title,
      company,
      location,
      description,
      applyUrl,
      url,
    },
  };
};

const leverExtract = (doc: Document, url: string): ExtractionResult => {
  const title =
    textFromSelectors(doc, ["h1", "[data-qa='posting-name']"]) ||
    metaContent(doc, ['meta[property="og:title"]']) ||
    null;
  const company =
    metaContent(doc, ['meta[property="og:site_name"]']) ||
    firstMatch([/\bTeam\s*[:\-]\s*([^\n|]+)/i], bodyText(doc)) ||
    null;
  const location =
    textFromSelectors(doc, [".location", "[data-qa='posting-location']"]) ||
    firstMatch([/\bLocation\s*[:\-]\s*([^\n|]+)/i], bodyText(doc));
  const description =
    textFromSelectors(doc, [
      ".posting-description",
      "[data-qa='posting-description']",
      "main",
    ]) || bodyText(doc);
  const applyUrl = metaContent(doc, ['meta[property="og:url"]']) || url;

  if (!title || !company || !description) {
    return { job: null, reason: "Unable to extract complete Lever job data." };
  }

  return {
    job: {
      source: "lever",
      title,
      company,
      location,
      description,
      applyUrl,
      url,
    },
  };
};

const ashbyExtract = (doc: Document, url: string): ExtractionResult => {
  const title =
    textFromSelectors(doc, ["h1", "[data-testid='job-title']"]) ||
    metaContent(doc, ['meta[property="og:title"]']) ||
    null;
  const company =
    metaContent(doc, ['meta[property="og:site_name"]']) ||
    firstMatch([/\bCompany\s*[:\-]\s*([^\n|]+)/i], bodyText(doc)) ||
    null;
  const location =
    textFromSelectors(doc, [".location", "[data-testid='location']"]) ||
    firstMatch([/\bLocation\s*[:\-]\s*([^\n|]+)/i], bodyText(doc));
  const description =
    textFromSelectors(doc, [
      ".job-description",
      "[data-testid='job-description']",
      "main",
    ]) || bodyText(doc);
  const applyUrl = metaContent(doc, ['meta[property="og:url"]']) || url;

  if (!title || !company || !description) {
    return { job: null, reason: "Unable to extract complete Ashby job data." };
  }

  return {
    job: {
      source: "ashby",
      title,
      company,
      location,
      description,
      applyUrl,
      url,
    },
  };
};

const workdayExtract = (doc: Document, url: string): ExtractionResult => {
  const title =
    textFromSelectors(doc, ["h1", "[data-automation-id='jobTitle']"]) ||
    metaContent(doc, ['meta[property="og:title"]']) ||
    null;
  const company =
    metaContent(doc, ['meta[property="og:site_name"]']) ||
    firstMatch([/\bOrganization\s*[:\-]\s*([^\n|]+)/i], bodyText(doc)) ||
    null;
  const location =
    textFromSelectors(doc, ["[data-automation-id='locations']", ".location"]) ||
    firstMatch([/\bLocation\s*[:\-]\s*([^\n|]+)/i], bodyText(doc));
  const description =
    textFromSelectors(doc, [
      "[data-automation-id='jobDescriptionText']",
      "main",
    ]) || bodyText(doc);
  const applyUrl = metaContent(doc, ['meta[property="og:url"]']) || url;

  if (!title || !company || !description) {
    return {
      job: null,
      reason: "Unable to extract complete Workday job data.",
    };
  }

  return {
    job: {
      source: "workday",
      title,
      company,
      location,
      description,
      applyUrl,
      url,
    },
  };
};

const linkedinExtract = (doc: Document, url: string): ExtractionResult => {
  const title =
    textFromSelectors(doc, [
      "h1",
      ".topcard__title",
      "[data-test-job-title]",
    ]) ||
    metaContent(doc, ['meta[property="og:title"]']) ||
    null;
  const company =
    textFromSelectors(doc, [
      ".topcard__org-name-link",
      ".topcard__flavor",
      "[data-test-job-company-name]",
    ]) ||
    metaContent(doc, ['meta[property="og:site_name"]']) ||
    null;
  const location =
    textFromSelectors(doc, [
      ".topcard__flavor--bullet",
      "[data-test-job-location]",
    ]) || firstMatch([/\bLocation\s*[:\-]\s*([^\n|]+)/i], bodyText(doc));
  const description =
    textFromSelectors(doc, [
      ".description__text",
      "[data-test-job-description]",
      "main",
    ]) || bodyText(doc);
  const applyUrl = metaContent(doc, ['meta[property="og:url"]']) || url;

  if (!title || !company || !description) {
    return {
      job: null,
      reason: "LinkedIn page must already be open and visible for extraction.",
    };
  }

  return {
    job: {
      source: "linkedin",
      title,
      company,
      location,
      description,
      applyUrl,
      url,
    },
  };
};

const genericExtract = (doc: Document, url: string): ExtractionResult => {
  const title =
    textFromSelectors(doc, ["h1", "title"]) ||
    metaContent(doc, ['meta[property="og:title"]']) ||
    null;
  const company =
    metaContent(doc, ['meta[property="og:site_name"]']) ||
    firstMatch([/\bCompany\s*[:\-]\s*([^\n|]+)/i], bodyText(doc)) ||
    new URL(url).hostname;
  const location =
    firstMatch([/\bLocation\s*[:\-]\s*([^\n|]+)/i], bodyText(doc)) || null;
  const description =
    textFromSelectors(doc, ["main", "article", "[role='main']"]) ||
    bodyText(doc);
  const applyUrl = metaContent(doc, ['meta[property="og:url"]']) || url;

  if (!title || !description) {
    return {
      job: null,
      reason: "Unable to extract enough visible job content.",
    };
  }

  return {
    job: {
      source: "generic",
      title,
      company,
      location,
      description,
      applyUrl,
      url,
    },
  };
};

export function extractJobDetails(
  document: Document,
  url: string,
): ExtractionResult {
  const source = detectSource(url, document);
  if (source === "greenhouse") {
    return greenhouseExtract(document, url);
  }
  if (source === "lever") {
    return leverExtract(document, url);
  }
  if (source === "ashby") {
    return ashbyExtract(document, url);
  }
  if (source === "workday") {
    return workdayExtract(document, url);
  }
  if (source === "linkedin") {
    return linkedinExtract(document, url);
  }
  return genericExtract(document, url);
}

export function toExtractionUiState(
  result: ExtractionResult,
): ExtractionUiState {
  if (!result.job) {
    return {
      source: null,
      title: "",
      company: "",
      location: "",
      status: "needs-review",
      reason: result.reason,
    };
  }

  return {
    source: result.job.source,
    title: result.job.title,
    company: result.job.company,
    location: result.job.location ?? "",
    status: "extracted",
  };
}
