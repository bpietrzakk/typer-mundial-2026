# Dokumentacja czutka

czutka to typer wyników meczów piłkarskich dla znajomych. Powstał jako typer Mundialu 2026 i jest przebudowywany w aplikację obsługującą wiele rozgrywek naraz (Liga Mistrzów, ligi top 5). Ten folder opisuje, jak aplikacja jest zbudowana i dlaczego.

Zacznij od głównego [README](../README.md), jeśli chcesz tylko uruchomić projekt lokalnie.

## Spis treści

- [data-model.md](data-model.md) — jak baza przechowuje rozgrywki, sezony, rundy, mecze, typy i profile punktacji; co zostało z wersji mundialowej.
- [scoring.md](scoring.md) — zasady punktacji, wynik po 90 minutach, kiedy można typować, korekty wyników, remisy w rankingu, bonusy w ligach.
- [data-source.md](data-source.md) — dlaczego football-data.org, czego nie obejmuje, jak warstwa dostawcy tłumaczy dane API (w tym pułapka z dogrywką i karnymi).
- [migrations.md](migrations.md) — jak działają migracje, jak je cofnąć, jak sprawdzić, że dane się nie zmieniły, procedura na produkcji.
- [ci-cd.md](ci-cd.md) — co sprawdzają automatyczne testy na GitHubie i jak zmiana trafia na produkcję (Vercel + Render + Neon).
- [decisions.md](decisions.md) — dziennik decyzji architektonicznych: co wybraliśmy, jakie były alternatywy i dlaczego. Nowe wpisy dopisuje się na końcu.

## Rozwój

- [rozwoj/do-zrobienia.md](rozwoj/do-zrobienia.md) — otwarte zadania i pomysły, krótko.
- [rozwoj/pomysly.md](rozwoj/pomysly.md) — historia testów UX i tego, co z nich wdrożono.
- [rozwoj/spec-kupon-tygodnia.md](rozwoj/spec-kupon-tygodnia.md) — specyfikacja kuponu tygodnia.
- [rozwoj/analiza-biznesowa.md](rozwoj/analiza-biznesowa.md), [monetyzacja.md](rozwoj/monetyzacja.md), [walidacja-b2b.md](rozwoj/walidacja-b2b.md) — czy i jak na tym zarobić.

Zrzuty ekranu: `screenshots/czutka-*.png` (obecna wersja), `screenshots/mundial-2026/` (wersja z Mundialu).
