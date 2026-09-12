(function () {
  var controls = document.getElementById('auth-controls');
  var notice = document.getElementById('auth-notice');
  var state = null;
  var googleConfig = null;
  function message(text) {
    if (notice) { notice.textContent = text || ''; notice.hidden = !text; }
  }
  function csrf() {
    var value = document.cookie.split('; ').find(function (v) { return v.indexOf('tickr_csrf=') === 0; });
    return value ? value.substring('tickr_csrf='.length) : '';
  }
  function request(url, body) {
    return fetch(url, body === undefined ? {} : {
      method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf()},
      body: JSON.stringify(body)
    }).then(function (response) { return response.json(); }).then(function (data) {
      if (!data.ok) throw new Error(data.error || 'Please try again.');
      return data;
    });
  }
  function applyState(data) {
    state = data;
    window.tickrAuth.state = data;
    window.dispatchEvent(new CustomEvent('tickr-auth', {detail: data}));
    if (!controls || !data.authenticated) return;
    controls.replaceChildren();
    if (location.pathname !== '/digest') {
      var digest = document.createElement('a');
      digest.href = '/digest'; digest.textContent = 'My digest'; controls.appendChild(digest);
    }
    var logout = document.createElement('button');
    logout.type = 'button'; logout.textContent = 'Sign out';
    logout.onclick = function () {
      logout.disabled = true;
      request('/api/auth/logout', {}).then(function () { window.location.assign('/'); })
        .catch(function (error) { message(error.message); logout.disabled = false; });
    };
    controls.appendChild(logout);
  }
  function signedIn(data) {
    applyState(data);
    if (data.needs_subscription) {
      window.openSubscribeModal();
    } else window.location.assign('/digest');
  }
  function renderGoogleButton() {
    if (!controls || !googleConfig || !window.google || !google.accounts || !google.accounts.id) return;
    controls.replaceChildren();
    google.accounts.id.renderButton(controls, {
      type: 'standard', theme: 'filled_blue', size: 'large', text: 'signin_with', shape: 'pill'
    });
  }
  window.addEventListener('tickr-theme-change', renderGoogleButton);
  window.tickrAuth = {state: null, csrf: csrf};
  try {
    var warning = sessionStorage.getItem('tickr-welcome-warning');
    if (warning) { message(warning); sessionStorage.removeItem('tickr-welcome-warning'); }
  } catch (error) {}
  window.tickrAuth.ready = request('/api/auth/config').then(function (config) {
    googleConfig = config;
    return request('/api/auth/session').then(function (data) {
      applyState(data);
      if (data.authenticated) {
        if (location.pathname !== '/digest' && data.needs_subscription && location.hash === '#subscribe') window.openSubscribeModal();
        return data;
      }
      if (!controls) return data;
      if (!config.enabled) {
        var unavailable = document.createElement('button');
        unavailable.type = 'button';
        unavailable.textContent = 'Sign in with Google';
        unavailable.disabled = true;
        unavailable.title = 'Google sign-in is not available yet. You can subscribe with email.';
        controls.replaceChildren();
        controls.appendChild(unavailable);
        return data;
      }
      var script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client'; script.async = true;
      script.onerror = function () { message('Google sign-in could not load. You can still subscribe with email.'); };
      script.onload = function () {
        google.accounts.id.initialize({client_id: config.client_id, callback: function (result) {
          message('Signing in…');
          request('/api/auth/google', {credential: result.credential})
            .then(function (result) { message(''); signedIn(result); })
            .catch(function (error) { message(error.message); });
        }});
        renderGoogleButton();
      };
      document.head.appendChild(script);
      return data;
    });
  }).catch(function (error) {
    message(error.message);
    return {authenticated: false};
  });
})();
