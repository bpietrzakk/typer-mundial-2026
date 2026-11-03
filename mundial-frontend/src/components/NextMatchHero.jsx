import NextMatchNotice from './NextMatchNotice';
import NextMatchPlay from './NextMatchPlay';

// top of the start screen: the nearest coupon match to type right here,
// the live one when everything started, or a short note (closed / empty week).
// hero = pickHeroMatch(matches), the parent also needs it to skip that row below
export default function NextMatchHero({ hero, matches, onSaved, onLocked, onKickoff, jokerOf, leaguesOf }) {
  if (hero.kind === 'empty') {
    return (
      <NextMatchNotice
        title="W tym tygodniu kupon jest pusty"
        text="Pewnie przerwa na mecze reprezentacji. Pojedyncze mecze możesz typować w zakładce Mecze."
      />
    );
  }

  if (hero.kind === 'closed') {
    const typed = matches.filter((m) => m.my_prediction).length;
    return (
      <NextMatchNotice
        title="Kupon na ten tydzień zamknięty"
        text={`Wytypowane: ${typed} z ${matches.length}. Nowy kupon w poniedziałek, a pojedyncze mecze możesz typować w zakładce Mecze.`}
      />
    );
  }

  // key = a fresh form when the hero moves on to the next match
  return (
    <NextMatchPlay
      key={hero.match.id}
      match={hero.match}
      live={hero.kind === 'live'}
      onSaved={onSaved}
      onLocked={onLocked}
      onKickoff={onKickoff}
      joker={jokerOf?.(hero.match)}
      leagues={leaguesOf?.(hero.match)}
    />
  );
}
