export const ASSESSMENT_STATUSES = [
  "queued",
  "running",
  "completed",
  "failed",
  "cancelled",
];

export const SEVERITIES = ["critical", "high", "medium", "low", "info"];

export const DOMAIN_KEYS = [
  "identity",
  "security",
  "compliance",
  "collaboration",
  "licensing",
];

export const DOMAIN_LABELS = {
  identity: "Identity",
  security: "Security",
  compliance: "Compliance",
  collaboration: "Collaboration",
  licensing: "Licensing",
};

/**
 * @typedef {Object} Assessment
 * @property {string} id
 * @property {string} tenant_id
 * @property {string} status
 * @property {number} progress_pct
 * @property {?number} overall_score
 * @property {?number} identity_score
 * @property {?number} security_score
 * @property {?number} compliance_score
 * @property {?number} collaboration_score
 * @property {?number} licensing_score
 * @property {?number} total_findings
 * @property {?number} critical_findings
 * @property {?number} high_findings
 * @property {?string} report_path
 * @property {string} created_at
 * @property {string} updated_at
 */

/**
 * @typedef {Object} Finding
 * @property {string} id
 * @property {string} assessment_id
 * @property {string} parameter_id
 * @property {?string} rule_id
 * @property {string} status
 * @property {*} raw_value
 * @property {?string} evaluated_value
 * @property {?string} severity
 * @property {?number} score_contribution
 */

/**
 * @typedef {Object} Recommendation
 * @property {string} id
 * @property {string} title
 * @property {string} severity
 * @property {string[]} remediation_steps
 * @property {string} impact
 * @property {number} priority_score
 */

/**
 * @typedef {Object} TimelineEvent
 * @property {string} id
 * @property {string} type
 * @property {string} title
 * @property {string} timestamp
 * @property {string} status
 */

/**
 * @typedef {Object} ScoreBreakdown
 * @property {string} assessment_id
 * @property {?number} overall_score
 * @property {Object.<string, ?number>} categories
 * @property {string} status
 */
