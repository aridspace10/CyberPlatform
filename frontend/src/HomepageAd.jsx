import { useEffect, useRef } from "react";

const adsEnabled = import.meta.env.VITE_ADS_ENABLED === "true";
const adClient = import.meta.env.VITE_ADSENSE_CLIENT?.trim();
const adSlot = import.meta.env.VITE_ADSENSE_SLOT?.trim();

export default function HomepageAd() {
  const requestedAd = useRef(false);
  const isPreview = import.meta.env.DEV;
  const hasAdConfig = Boolean(adClient && adSlot);

  useEffect(() => {
    if (!adsEnabled || isPreview || !hasAdConfig || requestedAd.current) return;

    requestedAd.current = true;
    if (!document.getElementById("cyberplatform-adsense-script")) {
      const script = document.createElement("script");
      script.id = "cyberplatform-adsense-script";
      script.async = true;
      script.crossOrigin = "anonymous";
      script.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${encodeURIComponent(adClient)}`;
      document.head.appendChild(script);
    }

    window.adsbygoogle = window.adsbygoogle || [];
    window.adsbygoogle.push({});
  }, [hasAdConfig, isPreview]);

  if (!adsEnabled || (!isPreview && !hasAdConfig)) return null;

  return (
    <section className="home-ad" aria-label="Advertisement">
      <div className="home-ad-heading"><span>ADVERTISEMENT</span><span>SUPPORTS THE SANDBOX</span></div>
      {isPreview ? (
        <div className="home-ad-preview" role="note">
          <span>AD SPACE PREVIEW</span>
          <p>A responsive Google ad will appear here after site approval.</p>
        </div>
      ) : (
        <ins
          className="adsbygoogle home-ad-unit"
          style={{ display: "block" }}
          data-ad-client={adClient}
          data-ad-slot={adSlot}
          data-ad-format="auto"
          data-full-width-responsive="true"
        />
      )}
    </section>
  );
}
