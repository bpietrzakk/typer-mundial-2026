// small arrow glued to the nick in the ranking, so it is clear the row opens the player's picks.
// plain text right after the nick (no space), so on a phone it never wraps to its own line
export default function SeePicksChevron() {
  return (
    <span
      aria-hidden="true"
      className="ml-1 font-bold text-gray-500 group-hover:text-gray-300 group-focus-visible:text-gray-300 transition-colors"
    >
      ›
    </span>
  );
}
