import api from './axios';

export const changeNick = (nick) =>
  api.patch('/auth/profile', { nick }).then((r) => r.data);

export const changePassword = (current_password, new_password) =>
  api.post('/auth/change-password', { current_password, new_password });

export const deleteAccount = (password) =>
  api.delete('/auth/account', { data: { password } });

export const adminDeleteUser = (userId) =>
  api.delete(`/admin/users/${userId}`);
