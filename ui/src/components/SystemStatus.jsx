function SystemStatus({status , onShowDetails}){
  return (
    <section>
      <h2>System Status</h2>
      <p>{status}</p>
      <button onClick={onShowDetails}>Show Details</button>
    </section>
  )
}

export default SystemStatus;