(() => {
  const track = document.querySelector('.home-ai-companion');
  const walker = track?.querySelector('.home-robot-walker');
  if (!walker || !walker.animate) return;

  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const random = (min, max) => min + Math.random() * (max - min);
  const robotWidth = walker.offsetWidth;
  const position = fraction => `translateX(calc(${fraction * 100}cqw - ${fraction * robotWidth}px))`;
  const gestures = ['idle', 'wobble', 'wave', 'look'];
  let fraction = .12, visible = true, active = false, timer, movement;
  let previous = 'idle';
  walker.style.transform = position(fraction);

  function next() {
    if (!active) return;
    // Mix short strolls, longer crossings, and stationary gestures.
    if (previous !== 'walk' || Math.random() < .35) {
      const destination = Math.max(.04, Math.min(.96,
        fraction + (Math.random() < .5 ? -1 : 1) * random(.12, .55)));
      const distance = Math.abs(destination - fraction) * Math.max(0, track.clientWidth - robotWidth);
      if (distance > 3) {
        track.dataset.action = previous = 'walk';
        movement = walker.animate([
          {transform: position(fraction)},
          {transform: position(destination)}
        ], {duration: Math.max(1300, distance / random(10, 16) * 1000), easing: 'cubic-bezier(.3,0,.7,1)', fill: 'forwards'});
        const current = movement;
        current.finished.then(() => {
          if (movement !== current || !active) return;
          fraction = destination;
          walker.style.transform = position(fraction);
          current.cancel();
          movement = null;
          rest();
        }).catch(() => {}); // Cancellation is expected when hidden or motion is disabled.
        return;
      }
    }
    rest();
  }

  function rest() {
    const options = gestures.filter(action => action !== previous);
    track.dataset.action = previous = options[Math.floor(Math.random() * options.length)];
    timer = setTimeout(next, previous === 'idle' ? random(1800, 4200) : random(2600, 3600));
  }

  function sync() {
    const shouldRun = visible && !document.hidden && !motion.matches;
    if (active === shouldRun) return;
    active = shouldRun;
    if (active) {
      timer = setTimeout(next, random(500, 1400));
    } else {
      clearTimeout(timer);
      if (movement) {
        const width = track.clientWidth - robotWidth;
        const offset = walker.getBoundingClientRect().left - track.getBoundingClientRect().left;
        fraction = width > 0 ? Math.max(0, Math.min(1, offset / width)) : 0;
        walker.style.transform = position(fraction);
        movement.cancel();
        movement = null;
      }
      track.dataset.action = 'idle';
    }
  }

  document.addEventListener('visibilitychange', sync);
  motion.addEventListener('change', sync);
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      sync();
    }).observe(track);
  }
  sync();
})();
