import { useState } from "react";

export function WorldGallery() {
  const [detail, setDetail] = useState(false);
  const src = detail ? "/images/solaris-light-study" : "/images/solaris-world";
  return (
    <figure className="world-gallery">
      <div className="world-image">
        <picture>
          <source media="(max-width: 680px)" srcSet={`${src}-mobile.webp`} />
          <img
            src={`${src}.webp`}
            width="3200"
            height="2000"
            loading="lazy"
            decoding="async"
            alt={
              detail
                ? "Raking light reveals oak joinery, woven linen and the mineral surface of stone"
                : "A sunlit courtyard home extends past an oculus and reflection pool into a planted landscape"
            }
          />
        </picture>
      </div>
      <figcaption>
        <span>{detail ? "Linen, oak and afternoon light." : "A courtyard shaped by the sun."}</span>
        <fieldset className="world-view-controls" aria-label="Architectural render view">
          <button type="button" aria-pressed={!detail} onClick={() => setDetail(false)}>
            The space
          </button>
          <button type="button" aria-pressed={detail} onClick={() => setDetail(true)}>
            The detail
          </button>
        </fieldset>
      </figcaption>
    </figure>
  );
}
