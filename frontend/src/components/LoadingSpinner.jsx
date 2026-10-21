function LoadingSpinner() {
  return (
    <div className="loading-container" role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true"></div>

      <h3>Analyzing support ticket</h3>

      <p>Retrieving knowledge and determining the appropriate action...</p>
    </div>
  );
}

export default LoadingSpinner;
