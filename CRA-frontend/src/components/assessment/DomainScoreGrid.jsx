import { BadgeCheck, BriefcaseBusiness, FileCheck2, ShieldCheck, UsersRound } from "lucide-react";
import ScoreCard from "./ScoreCard";
import { buildDomainScores } from "../../utils/assessmentFormatters";

const ICONS = {
  identity: UsersRound,
  security: ShieldCheck,
  compliance: FileCheck2,
  collaboration: BriefcaseBusiness,
  licensing: BadgeCheck,
};

export default function DomainScoreGrid({ assessment, scores }) {
  const domainScores = buildDomainScores(assessment, scores);
  return (
    <section className="domain-grid">
      {domainScores.map((domain) => (
        <ScoreCard
          key={domain.key}
          label={domain.label}
          value={domain.score}
          status={domain.status}
          trend={domain.trend}
          icon={ICONS[domain.key]}
        />
      ))}
    </section>
  );
}
