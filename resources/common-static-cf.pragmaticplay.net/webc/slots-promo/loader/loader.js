(() => {
  const VERSION = '0.1.5';

  const basePath = window.promoBasePath;

  if (!basePath) {
    console.error('promoBasePath is not set');
    return;
  }

  const isMobile = window.isMobile;

  const script = document.createElement('script');
  const bundleName = isMobile ? 'slots-promotions' : 'slots-promotions-desktop';
  script.src = `${basePath}/webc/slots-promo/${VERSION}/${bundleName}.bundle.js`;
  script.async = true;
  script.crossOrigin = 'anonymous';
  window.slotsPromotionsVersion = VERSION;

  script.onload = () => {
    console.log(`${bundleName} bundle v${VERSION} loaded`);
    window.slotsPromotionsLoaded = true;
    window.dispatchEvent(new Event('slots-promotions-ready'));
  };

  script.onerror = () => {
    console.error(`${bundleName} bundle v${VERSION} failed to load`);
    window.slotsPromotionsLoaded = false;
    window.slotsPromotionsVersion = undefined;
    window.dispatchEvent(new Event('slots-promotions-failed'));
  };
  document.head.appendChild(script);
})();
