// titled glass card for text sections
export default function InfoCard({ title, children }) {
  return (
    <div className="glass-card p-5 mb-6">
      <h2 className="font-semibold text-gray-200 mb-3">{title}</h2>
      {children}
    </div>
  );
}
