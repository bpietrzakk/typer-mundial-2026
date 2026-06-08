import { useState, useEffect } from 'react';

export default function InstallPrompt() {
  const [prompt, setPrompt] = useState(null);
  const [show, setShow] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (localStorage.getItem('pwa-install-dismissed')) return;

    const handler = (e) => {
      e.preventDefault();
      setPrompt(e);
      setShow(true);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const handleInstall = async () => {
    if (!prompt) return;
    prompt.prompt();
    const { outcome } = await prompt.userChoice;
    if (outcome === 'accepted') setShow(false);
    setPrompt(null);
  };

  const handleDismiss = () => {
    setShow(false);
    setDismissed(true);
    localStorage.setItem('pwa-install-dismissed', '1');
  };

  if (!show || dismissed) return null;

  return (
    <div className="fixed bottom-20 md:bottom-6 left-4 right-4 md:left-auto md:right-6 md:w-80 z-40 animate-slide-up">
      <div className="glass-card p-4 border-mundial-teal/30 shadow-glow-teal">
        <div className="flex items-start gap-3">
          <img src="/favicon.svg" alt="" className="w-10 h-10 rounded-xl shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-gray-200 text-sm">Zainstaluj Mundial Typer</p>
            <p className="text-xs text-gray-500 mt-0.5">Dodaj do ekranu głównego i korzystaj jak z aplikacji</p>
          </div>
          <button onClick={handleDismiss} className="text-gray-600 hover:text-gray-400 transition-colors shrink-0">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="flex gap-2 mt-3">
          <button onClick={handleInstall} className="btn-primary text-xs !py-2 !px-4 flex-1">
            Zainstaluj
          </button>
          <button onClick={handleDismiss} className="btn-secondary text-xs !py-2 !px-4">
            Nie teraz
          </button>
        </div>
      </div>
    </div>
  );
}
