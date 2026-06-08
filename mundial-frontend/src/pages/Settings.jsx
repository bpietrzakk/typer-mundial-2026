import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { changeNick, changePassword, deleteAccount, adminDeleteUser } from '../api/settings';
import { getUsers as getAdminUsers } from '../api/admin';
import PasswordInput from '../components/PasswordInput';

function Section({ title, description, children }) {
  return (
    <div className="glass-card p-6">
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-gray-200">{title}</h2>
        {description && <p className="text-sm text-gray-500 mt-0.5">{description}</p>}
      </div>
      {children}
    </div>
  );
}

export default function Settings() {
  const { user, logout, updateUser } = useAuth();
  const { addToast } = useToast();
  const navigate = useNavigate();

  // nick
  const [nick, setNick] = useState(user?.nick || '');
  const [nickLoading, setNickLoading] = useState(false);

  // password
  const [currentPwd, setCurrentPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [confirmPwd, setConfirmPwd] = useState('');
  const [pwdLoading, setPwdLoading] = useState(false);

  // delete own account
  const [deleteConfirmNick, setDeleteConfirmNick] = useState('');
  const [deletePwd, setDeletePwd] = useState('');
  const [deleteLoading, setDeleteLoading] = useState(false);

  // admin: user list
  const [adminUsers, setAdminUsers] = useState([]);
  const [adminSearch, setAdminSearch] = useState('');
  const [deletingUserId, setDeletingUserId] = useState(null);
  const [confirmDeleteUserId, setConfirmDeleteUserId] = useState(null);

  useEffect(() => {
    if (user?.is_admin) {
      getAdminUsers().then(setAdminUsers).catch(() => {});
    }
  }, [user]);

  const handleNickSave = async (e) => {
    e.preventDefault();
    if (nick === user?.nick) return;
    setNickLoading(true);
    try {
      const updated = await changeNick(nick);
      updateUser(updated);
      addToast('Nick zmieniony!');
    } catch (err) {
      addToast(err.response?.data?.detail || 'Nie udało się zmienić nicku', 'error');
    } finally {
      setNickLoading(false);
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    if (newPwd.length < 8) {
      addToast('Nowe hasło musi mieć min. 8 znaków', 'error');
      return;
    }
    if (newPwd !== confirmPwd) {
      addToast('Hasła nie są identyczne', 'error');
      return;
    }
    setPwdLoading(true);
    try {
      await changePassword(currentPwd, newPwd);
      setCurrentPwd('');
      setNewPwd('');
      setConfirmPwd('');
      addToast('Hasło zmienione!');
    } catch (err) {
      addToast(err.response?.data?.detail || 'Nie udało się zmienić hasła', 'error');
    } finally {
      setPwdLoading(false);
    }
  };

  const handleDeleteAccount = async (e) => {
    e.preventDefault();
    if (deleteConfirmNick !== user?.nick) {
      addToast('Nick się nie zgadza', 'error');
      return;
    }
    setDeleteLoading(true);
    try {
      await deleteAccount(deletePwd);
      await logout();
      navigate('/login', { replace: true });
    } catch (err) {
      addToast(err.response?.data?.detail || 'Nie udało się usunąć konta', 'error');
      setDeleteLoading(false);
    }
  };

  const handleAdminDelete = async (userId) => {
    if (confirmDeleteUserId !== userId) {
      setConfirmDeleteUserId(userId);
      return;
    }
    setDeletingUserId(userId);
    try {
      await adminDeleteUser(userId);
      setAdminUsers((prev) => prev.filter((u) => u.id !== userId));
      setConfirmDeleteUserId(null);
      addToast('Konto użytkownika usunięte');
    } catch (err) {
      addToast(err.response?.data?.detail || 'Nie udało się usunąć konta', 'error');
    } finally {
      setDeletingUserId(null);
    }
  };

  const filteredUsers = adminUsers.filter((u) =>
    u.nick.toLowerCase().includes(adminSearch.toLowerCase()) ||
    u.email.toLowerCase().includes(adminSearch.toLowerCase())
  );

  return (
    <div className="page-container max-w-2xl">
      <h1 className="page-title">Ustawienia</h1>

      <div className="space-y-6">

        {/* nick */}
        <Section title="Profil" description="Zmień swoją nazwę widoczną w rankingu">
          <form onSubmit={handleNickSave} className="flex gap-3">
            <input
              type="text"
              value={nick}
              onChange={(e) => setNick(e.target.value)}
              minLength={2}
              maxLength={32}
              className="input-field flex-1"
              placeholder="Twój nick"
            />
            <button
              type="submit"
              disabled={nickLoading || nick === user?.nick || nick.length < 2}
              className="btn-primary text-sm !px-5 !py-2.5 whitespace-nowrap"
            >
              {nickLoading ? 'Zapisuję…' : 'Zapisz'}
            </button>
          </form>
          <p className="text-xs text-gray-600 mt-2">Email: {user?.email}</p>
        </Section>

        {/* password */}
        <Section title="Zmiana hasła" description="Musisz podać obecne hasło">
          <form onSubmit={handlePasswordChange} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1.5">
                Obecne hasło
              </label>
              <PasswordInput
                id="s-current-pwd"
                value={currentPwd}
                onChange={(e) => setCurrentPwd(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1.5">
                Nowe hasło
              </label>
              <PasswordInput
                id="s-new-pwd"
                value={newPwd}
                onChange={(e) => setNewPwd(e.target.value)}
                placeholder="Minimum 8 znaków"
                autoComplete="new-password"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1.5">
                Powtórz nowe hasło
              </label>
              <PasswordInput
                id="s-confirm-pwd"
                value={confirmPwd}
                onChange={(e) => setConfirmPwd(e.target.value)}
                placeholder="Powtórz hasło"
                autoComplete="new-password"
              />
            </div>
            <button
              type="submit"
              disabled={pwdLoading || !currentPwd || !newPwd || !confirmPwd}
              className="btn-primary text-sm"
            >
              {pwdLoading ? 'Zmieniam…' : 'Zmień hasło'}
            </button>
          </form>
        </Section>

        {/* danger zone */}
        <Section title="Strefa niebezpieczna" description="">
          <div className="border border-red-500/20 rounded-xl p-5 bg-red-500/5">
            <p className="text-sm font-semibold text-red-400 mb-1">Usuń konto</p>
            <p className="text-xs text-gray-500 mb-4">
              Usunięcie jest nieodwracalne. Znikają wszystkie Twoje typy, punkty i przynależność do lig.
              Wpisz swój nick <span className="text-gray-300 font-mono">{user?.nick}</span> oraz hasło, aby potwierdzić.
            </p>
            <form onSubmit={handleDeleteAccount} className="space-y-3">
              <input
                type="text"
                value={deleteConfirmNick}
                onChange={(e) => setDeleteConfirmNick(e.target.value)}
                placeholder={`Wpisz: ${user?.nick}`}
                className="input-field text-sm"
                autoComplete="off"
              />
              <PasswordInput
                id="s-delete-pwd"
                value={deletePwd}
                onChange={(e) => setDeletePwd(e.target.value)}
                placeholder="Twoje hasło"
                autoComplete="current-password"
              />
              <button
                type="submit"
                disabled={deleteLoading || deleteConfirmNick !== user?.nick || !deletePwd}
                className="px-5 py-2.5 rounded-xl text-sm font-semibold bg-red-500/15 border border-red-500/40 text-red-400 hover:bg-red-500/25 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {deleteLoading ? 'Usuwam…' : 'Usuń konto permanentnie'}
              </button>
            </form>
          </div>
        </Section>

        {/* admin: user management */}
        {user?.is_admin && (
          <Section title="Zarządzanie użytkownikami" description="Widoczne tylko dla adminów">
            <input
              type="text"
              value={adminSearch}
              onChange={(e) => setAdminSearch(e.target.value)}
              placeholder="Szukaj po nicku lub emailu…"
              className="input-field text-sm mb-4"
            />
            <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
              {filteredUsers.map((u) => (
                <div
                  key={u.id}
                  className="flex items-center justify-between gap-3 px-4 py-3 rounded-xl bg-surface-700/30 border border-surface-500/10"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-200 truncate">{u.nick}</p>
                    <p className="text-xs text-gray-500 truncate">{u.email}</p>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-xs text-gray-500 tabular-nums">{u.total_points} pkt</span>
                    {confirmDeleteUserId === u.id ? (
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleAdminDelete(u.id)}
                          disabled={deletingUserId === u.id}
                          className="text-xs px-3 py-1.5 rounded-lg bg-red-500/20 border border-red-500/40 text-red-400 hover:bg-red-500/30 transition-colors"
                        >
                          {deletingUserId === u.id ? '…' : 'Potwierdź'}
                        </button>
                        <button
                          onClick={() => setConfirmDeleteUserId(null)}
                          className="text-xs px-3 py-1.5 rounded-lg bg-surface-600/50 text-gray-400 hover:text-gray-200 transition-colors"
                        >
                          Anuluj
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => handleAdminDelete(u.id)}
                        className="text-xs px-3 py-1.5 rounded-lg bg-surface-600/30 text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                      >
                        Usuń
                      </button>
                    )}
                  </div>
                </div>
              ))}
              {filteredUsers.length === 0 && (
                <p className="text-sm text-gray-500 text-center py-4">Brak wyników</p>
              )}
            </div>
          </Section>
        )}

      </div>
    </div>
  );
}
