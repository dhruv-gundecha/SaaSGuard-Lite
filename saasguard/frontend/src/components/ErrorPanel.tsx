export function ErrorPanel({
  title = "Request failed",
  message,
}: {
  title?: string;
  message: string;
}) {
  return (
    <div className="error-panel">
      <strong>{title}</strong>
      <p>{message}</p>
    </div>
  );
}
