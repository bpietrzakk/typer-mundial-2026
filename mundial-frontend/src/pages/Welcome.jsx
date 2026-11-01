import { useState } from 'react';
import WelcomeCompetitionsStep from '../components/WelcomeCompetitionsStep';
import WelcomeLeagueStep from '../components/WelcomeLeagueStep';

const STEPS = 2;

// /witaj — short onboarding right after sign-up without an invite link:
// 1) what do you predict (follow competitions), 2) who do you play with
export default function Welcome() {
  const [step, setStep] = useState(1);

  return (
    <div className="auth-bg min-h-screen flex items-start sm:items-center justify-center px-4 py-8">
      <div className="relative w-full max-w-lg animate-fade-in">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <img src="/favicon.svg" alt="" className="w-8 h-8 rounded-lg" />
            <span className="font-extrabold text-xl tracking-tight gradient-text">czutka</span>
          </div>
          <span className="text-xs text-gray-500 tabular-nums">Krok {step} z {STEPS}</span>
        </div>

        {/* progress dots */}
        <div className="flex gap-2 mb-6" aria-hidden="true">
          {Array.from({ length: STEPS }, (_, i) => (
            <span key={i} className={`h-1 flex-1 rounded-full ${i < step ? 'bg-mundial-teal' : 'bg-surface-600/60'}`} />
          ))}
        </div>

        <div className="glass-card p-6 sm:p-8">
          {step === 1
            ? <WelcomeCompetitionsStep onNext={() => setStep(2)} />
            : <WelcomeLeagueStep onBack={() => setStep(1)} />}
        </div>
      </div>
    </div>
  );
}
