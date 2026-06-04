import { motion } from "framer-motion";

export default function RecommendationCard({ recommendation }) {
  return (
    <motion.article
      className="recommendation-card"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      <div className="recommendation-topline">
        <span className={`severity severity-${recommendation.severity}`}>
          {recommendation.severity}
        </span>
        <strong>{recommendation.priority_score}</strong>
      </div>
      <h3>{recommendation.title}</h3>
      <p>{recommendation.impact}</p>
      <ol>
        {recommendation.remediation_steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
    </motion.article>
  );
}
