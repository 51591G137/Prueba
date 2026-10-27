/* Usuarios: elegir uno, crear, editar el nombre y borrar. */
import { api } from '../core/api.js';
import { field, h, listOf, loading } from '../core/dom.js';
import { leave, navigate } from '../core/router.js';
import { confirmDialog, guarded, onSubmit, setScreen, toast } from '../core/ui.js';

const TITLE = 'Gestión del restaurante';

export async function viewUsers({ stale }) {
  setScreen(TITLE, null, loading());
  // Comprobar si ya hay una sesión activa
  const me = await api.get('/api/auth/me').catch(() => null);
  if (me && me.id) {
    navigate(`#/u/${me.id}`);
    return;
  }
  const users = await api.get('/api/users');
  if (stale()) return;

  const loginForm = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data) => {
        const res = await api.post('/api/auth/login', data);
        if (res.token) localStorage.setItem('staff_token', res.token);
        toast(`Sesión iniciada como ${res.user.username}`);
        navigate(`#/u/${res.user.id}`);
      }),
    },
    h('h2', null, 'Iniciar sesión'),
    field('Usuario', h('input', { name: 'username', type: 'text', required: true, maxlength: 80, autocomplete: 'username' })),
    field('Contraseña', h('input', { name: 'password', type: 'password', maxlength: 128, autocomplete: 'current-password' })),
    h('button', { class: 'btn', type: 'submit' }, 'Entrar'),
    h('p', { class: 'small muted', style: 'margin-top: 1rem;' }, h('a', { href: '#/olvide-clave' }, '¿Has olvidado tu contraseña?')),
  );

  const registerForm = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data) => {
        const user = await api.post('/api/users', data);
        const res = await api.post('/api/auth/login', { username: data.username, password: data.password });
        if (res.token) localStorage.setItem('staff_token', res.token);
        toast('Usuario creado y sesión iniciada');
        navigate(`#/u/${user.id}`);
      }),
    },
    h('h2', null, 'Crear usuario'),
    field('Usuario', h('input', { name: 'username', type: 'text', required: true, maxlength: 80, autocomplete: 'off' })),
    field('Correo electrónico (para recuperar contraseña)', h('input', { name: 'email', type: 'email', maxlength: 120, autocomplete: 'email' })),
    field('Contraseña (opcional)', h('input', { name: 'password', type: 'password', maxlength: 128, autocomplete: 'new-password' })),
    h('button', { class: 'btn secondary', type: 'submit' }, 'Crear y entrar'),
  );

  setScreen(
    TITLE,
    null,
    loginForm,
    users.length === 0
      ? registerForm
      : h('details', { class: 'panel' }, h('summary', null, '¿Nuevo usuario? Regístralo aquí'), registerForm),
  );
}

export async function viewUserEdit({ params, stale }) {
  const { uid } = params;
  setScreen('Editar usuario', '#/', loading());
  const [user, restaurants] = await Promise.all([api.get(`/api/users/${uid}`), api.get(`/api/users/${uid}/restaurants`)]);
  if (stale()) return;

  const form = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data) => {
        await api.patch(`/api/users/${uid}`, data);
        toast('Cambios guardados');
        leave('#/');
      }),
    },
    h('h2', null, 'Datos del usuario'),
    field('Nombre de usuario', h('input', { name: 'username', type: 'text', value: user.username, required: true, maxlength: 80 })),
    field('Correo electrónico', h('input', { name: 'email', type: 'email', value: user.email || '', maxlength: 120 })),
    field('Nueva contraseña (opcional)', h('input', { name: 'password', type: 'password', maxlength: 128, placeholder: 'Dejar en blanco para conservar la actual' })),
    h('button', { class: 'btn', type: 'submit' }, 'Guardar cambios'),
  );

  const remove = guarded(async () => {
    const n = restaurants.length;
    const confirmed = await confirmDialog({
      title: `¿Borrar a ${user.username}?`,
      message: n
        ? `Se borrarán también los restaurantes que solo gestiona este usuario (${n} en total), con todas sus mesas, menú, comandas, facturas y reservas. No se puede deshacer.`
        : 'No se puede deshacer.',
      confirmLabel: 'Borrar usuario',
      danger: true,
    });
    if (!confirmed) return;
    await api.del(`/api/users/${uid}`);
    toast('Usuario borrado');
    leave('#/');
  });

  setScreen(
    'Editar usuario',
    '#/',
    form,
    h('div', { class: 'danger-zone' }, h('button', { class: 'btn danger', type: 'button', onclick: remove }, 'Borrar usuario')),
  );
}

export async function viewForgotPassword() {
  const form = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data) => {
        await api.post('/api/auth/forgot-password', data);
        toast('Si el correo está registrado, recibirás un enlace');
        navigate('#/');
      }),
    },
    h('h2', null, 'Recuperar contraseña'),
    h('p', { class: 'muted' }, 'Introduce tu correo y te enviaremos un enlace válido durante 1 hora para restablecerla.'),
    field('Correo electrónico', h('input', { name: 'email', type: 'email', required: true, maxlength: 120, autocomplete: 'email' })),
    h('button', { class: 'btn', type: 'submit' }, 'Enviar enlace'),
  );

  setScreen('Recuperar contraseña', '#/', form);
}

export async function viewResetPassword() {
  // Extraer token de la URL (?token=...)
  const hashParts = location.hash.split('?');
  const query = new URLSearchParams(hashParts[1] || '');
  const urlToken = query.get('token') || '';

  const form = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data) => {
        await api.post('/api/auth/reset-password', {
          token: data.token || urlToken,
          password: data.password,
        });
        toast('Contraseña restablecida con éxito. Ya puedes iniciar sesión.');
        navigate('#/');
      }),
    },
    h('h2', null, 'Nueva contraseña'),
    !urlToken && field('Token de restablecimiento', h('input', { name: 'token', type: 'text', required: true })),
    field('Nueva contraseña', h('input', { name: 'password', type: 'password', required: true, maxlength: 128, autocomplete: 'new-password' })),
    h('button', { class: 'btn', type: 'submit' }, 'Guardar nueva contraseña'),
  );

  setScreen('Restablecer contraseña', '#/', form);
}
