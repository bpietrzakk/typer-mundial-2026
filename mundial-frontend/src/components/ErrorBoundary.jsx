import { Component } from 'react';

// last safety net: an error while rendering shows this instead of a blank page.
// sits outside the router, so plain links and a full reload only
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error, info) {
    // keep the details in the console for debugging
    console.error('czutka: render error', error, info?.componentStack);
  }

  render() {
    if (!this.state.failed) return this.props.children;

    return (
      <div className="min-h-screen flex items-center justify-center px-4" role="alert">
        <div className="panel p-6 sm:p-8 max-w-sm w-full text-center animate-fade-in">
          <p className="text-4xl mb-3" aria-hidden="true">🥅</p>
          <h1 className="text-xl font-bold text-white mb-2">Coś poszło nie tak</h1>
          <p className="text-sm text-gray-400 mb-6">
            Ta strona się wyłożyła. Odśwież ją — Twoje zapisane typy są bezpieczne.
          </p>
          <div className="flex items-center justify-center gap-3">
            <button type="button" onClick={() => window.location.reload()} className="btn-primary text-sm">
              Odśwież
            </button>
            <a href="/" className="btn-secondary text-sm">Strona główna</a>
          </div>
        </div>
      </div>
    );
  }
}
