export type AutofillSource = "profile" | "answer-bank";

export type AutofillFieldKind =
  | "email"
  | "phone"
  | "full-name"
  | "first-name"
  | "last-name"
  | "location"
  | "company"
  | "title"
  | "linkedin"
  | "portfolio"
  | "github"
  | "website"
  | "work-authorization"
  | "salary"
  | "notice-period"
  | "relocation"
  | "custom"
  | "unknown";

export interface AutofillAnswerEntry {
  key: string;
  questionText: string;
  answerText: string;
  category: string;
  requiresReview: boolean;
}

export interface AutofillProfileData {
  profileId: string;
  fullName: string;
  email: string;
  phone: string;
  location: string;
  currentTitle: string;
  currentCompany: string;
  linkedinUrl?: string;
  portfolioUrl?: string;
  githubUrl?: string;
  websiteUrl?: string;
  workAuthorization?: string;
  answerBank: AutofillAnswerEntry[];
}

export interface AutofillFieldTarget {
  element: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;
  label: string;
  name: string;
  kind: AutofillFieldKind;
  required: boolean;
  selector: string;
}

export interface AutofillDecision {
  selector: string;
  label: string;
  fieldKind: AutofillFieldKind;
  status: "filled" | "needs-review" | "skipped";
  source?: AutofillSource;
  answerKey?: string;
  valuePreview?: string;
  reason?: string;
}

export interface AutofillResult {
  profileId: string;
  totalFields: number;
  filledCount: number;
  reviewCount: number;
  skippedCount: number;
  stopBeforeSubmit: true;
  decisions: AutofillDecision[];
}

const SENSITIVE_PATTERNS = [
  /salary/i,
  /compensation/i,
  /pay/i,
  /ethnicity/i,
  /race/i,
  /gender/i,
  /pronoun/i,
  /veteran/i,
  /disabil/i,
  /citizenship/i,
  /work authorization/i,
  /sponsor/i,
  /immigration/i,
  /criminal/i,
  /felon/i,
  /birthday/i,
  /date of birth/i,
  /ssn/i,
  /social security/i,
];

const FIELD_PATTERNS: Array<[AutofillFieldKind, RegExp[]]> = [
  ["email", [/\bemail\b/i, /e-mail/i, /contact email/i]],
  ["phone", [/phone/i, /mobile/i, /cell/i, /tel/i]],
  ["first-name", [/first name/i, /\bgiven name\b/i]],
  ["last-name", [/last name/i, /\bsurname\b/i, /\bfamily name\b/i]],
  ["full-name", [/full name/i, /\bname\b/i, /your name/i]],
  ["location", [/location/i, /city/i, /state/i, /address/i]],
  ["company", [/company/i, /current employer/i, /employer/i]],
  ["title", [/title/i, /role/i, /position/i, /current title/i]],
  ["linkedin", [/linkedin/i, /linked in/i]],
  ["portfolio", [/portfolio/i, /website/i, /site/i]],
  ["github", [/github/i, /git hub/i]],
  ["website", [/personal website/i, /\burl\b/i, /homepage/i]],
  ["work-authorization", [/work authorization/i, /authorized to work/i, /visa/i]],
  ["salary", [/salary/i, /compensation/i, /pay/i, /expected salary/i]],
  ["notice-period", [/notice period/i, /start date/i, /available/i]],
  ["relocation", [/relocat/i]],
];

const CUSTOM_PROFILE_KEYS: Record<AutofillFieldKind, keyof AutofillProfileData | null> = {
  email: "email",
  phone: "phone",
  "full-name": "fullName",
  "first-name": "fullName",
  "last-name": "fullName",
  location: "location",
  company: "currentCompany",
  title: "currentTitle",
  linkedin: "linkedinUrl",
  portfolio: "portfolioUrl",
  github: "githubUrl",
  website: "websiteUrl",
  "work-authorization": "workAuthorization",
  salary: null,
  "notice-period": null,
  relocation: null,
  custom: null,
  unknown: null,
};

const UNSUPPORTED_INPUT_TYPES = new Set([
  "button",
  "hidden",
  "image",
  "password",
  "reset",
  "submit",
  "file",
]);

const CONTROL_SELECTORS = ["input", "textarea", "select"].join(",");

const trim = (value: string | null | undefined): string => (value ?? "").trim();

const clean = (value: string | null | undefined): string =>
  trim(value).replace(/\s+/g, " ");

const normalize = (value: string | null | undefined): string =>
  clean(value).toLowerCase();

const escapeSelector = (value: string): string =>
  value.replace(/["\\]/g, "\\$&");

const isSensitiveLabel = (text: string): boolean =>
  SENSITIVE_PATTERNS.some((pattern) => pattern.test(text));

const matchesAny = (text: string, patterns: RegExp[]): boolean =>
  patterns.some((pattern) => pattern.test(text));

const detectFieldKind = (text: string): AutofillFieldKind => {
  const normalized = normalize(text);
  if (!normalized) {
    return "unknown";
  }

  for (const [kind, patterns] of FIELD_PATTERNS) {
    if (matchesAny(normalized, patterns)) {
      return kind;
    }
  }

  return "custom";
};

const readLabel = (doc: Document, element: Element): string => {
  const id = element.getAttribute("id");
  if (id) {
    const label = doc.querySelector(`label[for="${escapeSelector(id)}"]`);
    const labelText = clean(label?.textContent);
    if (labelText) {
      return labelText;
    }
  }

  const wrappingLabel = element.closest("label");
  const wrappingText = clean(wrappingLabel?.textContent);
  if (wrappingText) {
    return wrappingText;
  }

  const ariaLabel = clean(element.getAttribute("aria-label"));
  if (ariaLabel) {
    return ariaLabel;
  }

  const ariaLabelledBy = clean(element.getAttribute("aria-labelledby"));
  if (ariaLabelledBy) {
    const referenced = ariaLabelledBy
      .split(/\s+/)
      .map((ref) => clean(doc.getElementById(ref)?.textContent))
      .filter(Boolean)
      .join(" ");
    if (referenced) {
      return referenced;
    }
  }

  const placeholder = clean(element.getAttribute("placeholder"));
  if (placeholder) {
    return placeholder;
  }

  return clean(
    [
      element.getAttribute("name"),
      element.getAttribute("id"),
      element.getAttribute("autocomplete"),
    ]
      .filter(Boolean)
      .join(" "),
  );
};

const selectorFor = (element: Element): string => {
  const id = element.getAttribute("id");
  if (id) {
    return `#${escapeSelector(id)}`;
  }

  const name = element.getAttribute("name");
  if (name) {
    return `${element.tagName.toLowerCase()}[name="${escapeSelector(name)}"]`;
  }

  return element.tagName.toLowerCase();
};

const inputType = (element: HTMLInputElement): string =>
  (element.getAttribute("type") || "text").toLowerCase();

const isInputElement = (element: Element): element is HTMLInputElement =>
  element.tagName.toLowerCase() === "input";

const isTextAreaElement = (
  element: Element,
): element is HTMLTextAreaElement => element.tagName.toLowerCase() === "textarea";

const isSelectElement = (element: Element): element is HTMLSelectElement =>
  element.tagName.toLowerCase() === "select";

const valuePreview = (value: string): string =>
  value.length > 48 ? `${value.slice(0, 45)}...` : value;

const setFieldValue = (
  element: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement,
  value: string,
): void => {
  const bindValue = (target: { value: string }, nextValue: string): void => {
    target.value = nextValue;
    if (target.value !== nextValue) {
      Object.defineProperty(target, "value", {
        configurable: true,
        enumerable: true,
        writable: true,
        value: nextValue,
      });
    }
  };

  if (isInputElement(element)) {
    const type = inputType(element);
    if (type === "checkbox" || type === "radio") {
      element.checked = value === "true";
      if (element.checked !== (value === "true")) {
        Object.defineProperty(element, "checked", {
          configurable: true,
          enumerable: true,
          writable: true,
          value: value === "true",
        });
      }
      element.setAttribute("checked", element.checked ? "true" : "false");
      return;
    }
  }

  if (isSelectElement(element)) {
    const lower = value.toLowerCase();
    for (const option of Array.from(element.options)) {
      const optionText = normalize(`${option.textContent} ${option.value}`);
      if (optionText.includes(lower) || lower.includes(optionText)) {
        bindValue(element, option.value);
        element.setAttribute("value", option.value);
        return;
      }
    }
  }

  bindValue(element, value);
  element.setAttribute("value", value);
  if (element.tagName.toLowerCase() === "textarea") {
    element.textContent = value;
  }
};

const dispatchChange = (
  element: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement,
): void => {
  const eventInit = { bubbles: true, cancelable: true };
  const EventCtor = element.ownerDocument?.defaultView?.Event ?? globalThis.Event;
  if (!EventCtor) {
    return;
  }
  element.dispatchEvent(new EventCtor("input", eventInit));
  element.dispatchEvent(new EventCtor("change", eventInit));
};

const fieldMatchesProfile = (
  kind: AutofillFieldKind,
  profile: AutofillProfileData,
): string | null => {
  if (kind === "first-name") {
    return clean(profile.fullName.split(/\s+/)[0] ?? "");
  }

  if (kind === "last-name") {
    const parts = profile.fullName.split(/\s+/).filter(Boolean);
    return clean(parts.at(-1) ?? "");
  }

  const key = CUSTOM_PROFILE_KEYS[kind];
  if (!key) {
    return null;
  }

  const value = profile[key];
  return typeof value === "string" && value.trim() ? clean(value) : null;
};

const findAnswerBankEntry = (
  profile: AutofillProfileData,
  label: string,
): AutofillAnswerEntry | null => {
  const normalizedLabel = normalize(label);
  if (!normalizedLabel) {
    return null;
  }

  return (
    profile.answerBank.find((entry) => {
      const normalizedQuestion = normalize(entry.questionText);
      return (
        normalizedQuestion.includes(normalizedLabel) ||
        normalizedLabel.includes(normalizedQuestion) ||
        normalize(entry.key).includes(normalizedLabel)
      );
    }) ?? null
  );
};

const isCheckboxOrRadio = (element: HTMLInputElement): boolean =>
  ["checkbox", "radio"].includes(inputType(element));

const getFieldTargets = (doc: Document): AutofillFieldTarget[] => {
  const targets: AutofillFieldTarget[] = [];
  const elements = doc.querySelectorAll(CONTROL_SELECTORS);

  elements.forEach((element) => {
    if (!isInputElement(element) && !isTextAreaElement(element) && !isSelectElement(element)) {
      return;
    }

    if (isInputElement(element)) {
      const type = inputType(element);
      if (UNSUPPORTED_INPUT_TYPES.has(type)) {
        return;
      }
    }

    const label = readLabel(doc, element);
    const name = clean(element.getAttribute("name"));
    const kind = detectFieldKind([label, name, clean(element.getAttribute("autocomplete"))].join(" "));
    targets.push({
      element,
      label,
      name,
      kind,
      required: element.hasAttribute("required"),
      selector: selectorFor(element),
    });
  });

  return targets;
};

const shouldAlwaysReview = (target: AutofillFieldTarget): boolean => {
  const text = normalize([target.label, target.name].join(" "));
  return isSensitiveLabel(text) || target.kind === "salary" || target.kind === "custom" && isSensitiveLabel(text);
};

const resolveTargetValue = (
  target: AutofillFieldTarget,
  profile: AutofillProfileData,
): {
  status: AutofillDecision["status"];
  source?: AutofillSource;
  answerKey?: string;
  value?: string;
  reason?: string;
} => {
  const sensitive = shouldAlwaysReview(target);
  const profileValue = fieldMatchesProfile(target.kind, profile);

  if (profileValue && !sensitive) {
    return {
      status: "filled",
      source: "profile",
      value: profileValue,
    };
  }

  const bankEntry = findAnswerBankEntry(profile, target.label);
  if (bankEntry) {
    if (bankEntry.requiresReview || sensitive) {
      return {
        status: "needs-review",
        source: "answer-bank",
        answerKey: bankEntry.key,
        value: bankEntry.answerText,
        reason: "Sensitive or flagged answer requires human review.",
      };
    }

    return {
      status: "filled",
      source: "answer-bank",
      answerKey: bankEntry.key,
      value: clean(bankEntry.answerText),
    };
  }

  if (profileValue) {
    return {
      status: "needs-review",
      source: "profile",
      value: profileValue,
      reason: "Field is sensitive and requires review before autofill.",
    };
  }

  return {
    status: "needs-review",
    reason: "No trusted profile or answer bank value matched this field.",
  };
};

export function detectAutofillTargets(document: Document): AutofillFieldTarget[] {
  return getFieldTargets(document);
}

export function buildAutofillPlan(
  document: Document,
  profile: AutofillProfileData,
): AutofillResult {
  const targets = getFieldTargets(document);
  const decisions: AutofillDecision[] = [];

  let filledCount = 0;
  let reviewCount = 0;
  let skippedCount = 0;

  for (const target of targets) {
    const resolved = resolveTargetValue(target, profile);
    const baseDecision: AutofillDecision = {
      selector: target.selector,
      label: target.label,
      fieldKind: target.kind,
      status: resolved.status,
      source: resolved.source,
      answerKey: resolved.answerKey,
      valuePreview: resolved.value ? valuePreview(resolved.value) : undefined,
      reason: resolved.reason,
    };

    if (resolved.status === "filled" && resolved.value) {
      setFieldValue(target.element, resolved.value);
      dispatchChange(target.element);
      filledCount += 1;
    } else if (resolved.status === "needs-review") {
      reviewCount += 1;
    } else {
      skippedCount += 1;
    }

    decisions.push(baseDecision);
  }

  return {
    profileId: profile.profileId,
    totalFields: targets.length,
    filledCount,
    reviewCount,
    skippedCount,
    stopBeforeSubmit: true,
    decisions,
  };
}

export function summarizeAutofillResult(result: AutofillResult): string {
  const parts = [
    `${result.filledCount} filled`,
    `${result.reviewCount} review`,
    `${result.skippedCount} skipped`,
  ];

  return `${parts.join(", ")}. Final submit blocked.`;
}
