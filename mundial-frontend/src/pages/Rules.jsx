import { Link } from 'react-router-dom';
import BulletList from '../components/BulletList';
import HitBadge from '../components/HitBadge';
import InfoCard from '../components/InfoCard';
import PointsTable from '../components/PointsTable';

// points per phase: [exact, diff, tendency]
const LEAGUE_ROWS = [
  { label: 'Każda kolejka', pts: [5, 3, 2] },
];

const UCL_ROWS = [
  { label: 'Faza ligowa i baraże', pts: [5, 3, 2] },
  { label: '1/8 finału', pts: [7, 4, 3] },
  { label: 'Ćwierćfinał', pts: [9, 5, 4] },
  { label: 'Półfinał', pts: [11, 6, 5] },
  { label: 'Finał', pts: [15, 8, 6] },
];

// wc2026 profile (002 seed / migration 005)
const WC_ROWS = [
  { label: 'Faza grupowa', pts: [5, 3, 2] },
  { label: '1/16 finału', pts: [6, 3, 2] },
  { label: '1/8 finału', pts: [7, 4, 3] },
  { label: 'Ćwierćfinał', pts: [9, 5, 4] },
  { label: 'Półfinał', pts: [11, 6, 5] },
  { label: 'Mecz o 3. miejsce', pts: [11, 6, 5] },
  { label: 'Finał', pts: [15, 8, 6] },
];

export default function Rules() {
  return (
    <div className="page-container max-w-2xl">
      <h1 className="page-title">Zasady punktacji</h1>

      {/* tiers */}
      <InfoCard title="Trzy progi, liczy się najwyższy">
        <p className="text-sm text-gray-500 mb-4">
          Za każdy rozliczony mecz dostajesz punkty za najlepsze trafienie. Przykłady dla typu 2:1:
        </p>
        <div className="space-y-4">
          <div className="flex items-start gap-3">
            <HitBadge hitType="exact" className="shrink-0 whitespace-nowrap" />
            <p className="text-sm text-gray-400">Wytypowałeś dokładnie taki wynik jak rzeczywisty — 2:1 i wynik 2:1.</p>
          </div>
          <div className="flex items-start gap-3">
            <HitBadge hitType="diff" className="shrink-0 whitespace-nowrap" />
            <p className="text-sm text-gray-400">
              Zgadza się różnica bramek, ale nie wynik — 2:1 i wynik 3:2 (obie różnice +1).
              Trafiony remis, który nie jest dokładny (np. 1:1 i wynik 2:2), zawsze dostaje punkty za różnicę bramek, nigdy za samego zwycięzcę.
            </p>
          </div>
          <div className="flex items-start gap-3">
            <HitBadge hitType="tendency" className="shrink-0 whitespace-nowrap" />
            <p className="text-sm text-gray-400">Trafiłeś tylko, kto wygrał — 2:1 i wynik 4:0.</p>
          </div>
          <div className="flex items-start gap-3">
            <HitBadge hitType="miss" className="shrink-0 whitespace-nowrap" />
            <p className="text-sm text-gray-400">Żaden próg — 2:1 i wynik 0:2. Zero punktów.</p>
          </div>
        </div>
      </InfoCard>

      {/* points per profile */}
      <h2 className="font-semibold text-gray-200 mb-3 px-1">Ile to punktów</h2>
      <PointsTable
        title="Ligi krajowe"
        subtitle="Premier League, LaLiga, Serie A, Bundesliga, Ligue 1"
        rows={LEAGUE_ROWS}
      />
      <div className="mb-6">
        <PointsTable
          title="Liga Mistrzów"
          subtitle="Stawka rośnie w fazie pucharowej"
          rows={UCL_ROWS}
        />
      </div>

      <InfoCard title="Liczy się wynik po 90 minutach">
        <BulletList items={[
          'Punktujemy wynik po regulaminowym czasie gry z doliczonym czasem.',
          'Dogrywka i rzuty karne nie mają znaczenia — finał 1:1 po 90 minutach, rozstrzygnięty w karnych, to dla typera remis 1:1.',
          'Dwumecz to dwa osobne mecze i dwa osobne typy.',
          'Gdy dostawca danych poprawi wynik po fakcie, punkty są przeliczane od nowa (do 24 godzin po rozliczeniu).',
        ]} />
      </InfoCard>

      <InfoCard title="Kiedy możesz typować">
        <BulletList items={[
          'Typ możesz dodać i zmieniać do godziny rozpoczęcia meczu. W chwili startu jest już za późno.',
          'Mecz przełożony albo przerwany jest zablokowany, dopóki nie dostanie nowego terminu — wtedy typowanie otwiera się znowu.',
          'Gdy godzina meczu nie jest jeszcze potwierdzona, widzisz tylko datę. Typowanie zamyka się według zapisanej godziny.',
          'Mecz odwołany albo zakończony walkowerem unieważnia typy — nie dostają punktów i nie liczą się do rankingu.',
        ]} />
      </InfoCard>

      <InfoCard title="Remisy w rankingu">
        <p className="text-sm text-gray-400 mb-3">
          Ranking sortuje po sumie punktów. Przy równej sumie decyduje:
        </p>
        <ol className="space-y-1.5 text-sm text-gray-400 list-decimal list-inside mb-3">
          <li>liczba dokładnych trafień,</li>
          <li>liczba trafionych różnic bramek,</li>
          <li>alfabetycznie nick.</li>
        </ol>
        <p className="text-sm text-gray-400">
          Gracze równi w punktach, dokładnych trafieniach i różnicach dzielą miejsce, a kolejne miejsce jest pomijane (1, 1, 3).
          Każdy sezon ma własny ranking — nowy sezon to czysta karta.
        </p>
      </InfoCard>

      <InfoCard title="Ligi prywatne">
        <BulletList items={[
          'Ranking ligi używa tych samych punktów co ranking rozgrywek, ale pokazuje tylko członków ligi.',
          'Właściciel może zawęzić ligę do wybranych rozgrywek — liczą się wtedy tylko ich mecze. Bez zawężenia liczą się wszystkie.',
          'Właściciel może dodać pytanie bonusowe „kto wygra sezon” z własną liczbą punktów (1–100) i terminem. Odpowiadasz do terminu, a cudze odpowiedzi widać dopiero po nim.',
          'Punkty z bonusu liczą się tylko w rankingu tej ligi i przyznawane są po rozstrzygnięciu sezonu.',
        ]} />
      </InfoCard>

      <PointsTable
        title="Archiwum: Mundial 2026"
        subtitle="Dawna tabela punktów — turniej jest zakończony"
        rows={WC_ROWS}
      />
      <div className="glass-card p-5">
        <p className="text-sm text-gray-400">
          Mundial 2026 zostaje w aplikacji jako archiwum: mecze, ranking i typy są tylko do odczytu.
          W tamtym turnieju były też bonusy — mistrz turnieju (+20 pkt) i awans z grupy (+3 pkt za drużynę).{' '}
          <Link to="/bonus" className="text-mundial-teal hover:underline">Zobacz swoje bonusy z Mundialu →</Link>
        </p>
      </div>
    </div>
  );
}
