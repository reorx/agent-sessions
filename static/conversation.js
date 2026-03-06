(function () {
  const navItems = document.querySelectorAll('.message[data-nav]');
  const navHint = document.getElementById('navHint');
  let currentIndex = -1;
  let hintTimer = null;

  function showHint() {
    navHint.classList.add('visible');
    clearTimeout(hintTimer);
    hintTimer = setTimeout(() => navHint.classList.remove('visible'), 2000);
  }

  function focusMessage(index) {
    if (index < 0 || index >= navItems.length) return;
    navItems.forEach((el) => el.classList.remove('focused'));
    currentIndex = index;
    navItems[currentIndex].classList.add('focused');
    var rect = navItems[currentIndex].getBoundingClientRect();
    if (rect.bottom < 0 || rect.top > window.innerHeight) {
      navItems[currentIndex].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'j' || e.key === 'ArrowDown') {
      e.preventDefault();
      if (currentIndex === -1) {
        focusMessage(0);
      } else {
        focusMessage(currentIndex + 1);
      }
      showHint();
    } else if (e.key === 'k' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (currentIndex === -1) {
        focusMessage(navItems.length - 1);
      } else {
        focusMessage(currentIndex - 1);
      }
      showHint();
    } else if (e.key === 'Escape') {
      navItems.forEach((el) => el.classList.remove('focused'));
      currentIndex = -1;
    }
  });

  navItems.forEach((el, idx) => {
    el.addEventListener('click', function () {
      focusMessage(idx);
    });
  });

  // Write-file fold/unfold
  document.querySelectorAll('.message.write-file').forEach((el) => {
    el.addEventListener('click', function (e) {
      // Only toggle if clicking the ::after toggle area (below the pre)
      // or if the pre is collapsed and user clicks anywhere on the message
      const pre = el.querySelector('pre');
      if (!el.classList.contains('expanded') && pre.scrollHeight <= pre.clientHeight) {
        // Content fits within visible lines, no need to toggle
        return;
      }
      el.classList.toggle('expanded');
      e.stopPropagation();
    });
  });

  // Show hint briefly on load
  setTimeout(showHint, 500);
})();
