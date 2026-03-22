import PropTypes from "prop-types";

function ThemeToggle({ isDark, onToggle }) {
  return (
    <button className="theme-toggle" onClick={onToggle} aria-label="Toggle color mode">
      <span className="toggle-dot" />
      <span>{isDark ? "Dark" : "Light"}</span>
    </button>
  );
}

ThemeToggle.propTypes = {
  isDark: PropTypes.bool.isRequired,
  onToggle: PropTypes.func.isRequired
};

export default ThemeToggle;
