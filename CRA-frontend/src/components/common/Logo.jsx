import logo from "../../assets/images/TPT-Logo.png";

const SIZES = {
  corner: 24,
  sidebar: 36,
  mobile: 40,
  hero: 64,
};

export default function Logo({ className = "", width, height, size, showText = false, style, ...rest }) {
  const resolvedHeight = height ?? SIZES[size] ?? 32;
  return (
    <>
      <img
        src={logo}
        alt="TPT Technologies"
        className={`inline-block h-auto w-auto max-w-full object-contain ${className}`}
        style={{ height: resolvedHeight, width, ...style }}
        {...rest}
      />
      {showText && <span className="sr-only">TPT Technologies</span>}
    </>
  );
}
