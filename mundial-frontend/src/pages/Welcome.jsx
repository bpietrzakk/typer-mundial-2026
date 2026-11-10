import WelcomeLeagueStep from '../components/WelcomeLeagueStep';

// /witaj — short onboarding right after sign-up without an invite link:
// who do you play with (create / join a league, or the global coupon alone).
// no competition step: my competitions come from my leagues
export default function Welcome() {
  return (
    <div className="auth-bg min-h-screen flex items-start sm:items-center justify-center px-4 py-8">
      <div className="relative w-full max-w-lg animate-fade-in">
        <div className="flex items-center gap-2 mb-6">
          <span className="wordmark text-2xl leading-none">czutka</span>
        </div>

        <div className="glass-card p-6 sm:p-8">
          <WelcomeLeagueStep />
        </div>
      </div>
    </div>
  );
}
