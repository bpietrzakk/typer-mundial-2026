// plain list of short sentences with a teal bullet
export default function BulletList({ items }) {
  return (
    <ul className="space-y-2.5 text-sm text-gray-400">
      {items.map((text) => (
        <li key={text} className="flex items-start gap-2.5">
          <span className="text-mundial-teal mt-0.5 shrink-0">•</span>
          <span>{text}</span>
        </li>
      ))}
    </ul>
  );
}
