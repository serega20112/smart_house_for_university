/** Shown while the first snapshot is loading, so the layout does not jump. */

export function Skeleton() {
  return (
    <div className="grid grid--devices">
      {[0, 1, 2, 3, 4, 5].map((index) => (
        <div key={index} className="skeleton skeleton--device" />
      ))}
    </div>
  );
}

export function LoadingBar() {
  return <div className="skeleton skeleton--bar" />;
}
