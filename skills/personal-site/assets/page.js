  function setMode(m){
    var card = m === 'card';
    document.body.classList.toggle('mode-card', card);
    document.body.classList.toggle('mode-profile', !card);
    var bc = document.getElementById('btn-card'), bp = document.getElementById('btn-profile');
    bc.classList.toggle('is-on', card);
    bp.classList.toggle('is-on', !card);
    bc.setAttribute('aria-pressed', card ? 'true' : 'false');
    bp.setAttribute('aria-pressed', card ? 'false' : 'true');
    if (history.replaceState) {
      history.replaceState(null, '', card ? '#card' : location.pathname);
    }
  }
  setMode(location.hash === '#card' ? 'card' : 'profile');

  function pick(key){
    document.querySelectorAll('.tab').forEach(function(t){
      var on = t.getAttribute('data-key') === key;
      t.classList.toggle('is-on', on);
      t.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    document.querySelectorAll('.qrpanel').forEach(function(p){
      p.hidden = p.getAttribute('data-key') !== key;
    });
  }

  document.querySelector('.tabs').addEventListener('keydown', function(e){
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    var tabs = [].slice.call(document.querySelectorAll('.tab'));
    var i = tabs.indexOf(document.activeElement);
    if (i < 0) return;
    e.preventDefault();
    var next = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
    next.focus();
    pick(next.getAttribute('data-key'));
  });
