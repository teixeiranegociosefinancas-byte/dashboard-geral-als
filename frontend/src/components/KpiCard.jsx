export default function KpiCard({ label, value, color = "cyan", meta, onClick }) {
  return (
    <div className={`card ${onClick ? "card-clickable" : ""}`} onClick={onClick}>
      <div className="card-label">{label}</div>
      <div className={`card-value ${color}`}>{value}</div>
      {meta && <div className="card-meta">{meta}</div>}
    </div>
  );
}
