const ChatOverlay = () => (
    <div
      style={{
        position: "fixed",
        bottom: 20,
        right: 20,
        width: 350,
        height: 500,
        background: "white",
        boxShadow: "0 8px 24px rgba(0,0,0,0.18)",
        borderRadius: 8,
        zIndex: 999999,
        display: "flex",
        flexDirection: "column",
        padding: 12
      }}
    >
      <h2>Chat Widget</h2>
      <div style={{ flex: 1, overflow: "auto", marginBottom: 12 }}>Chat messages here</div>
      <input
        placeholder="Type a message..."
        style={{ width: "100%", padding: 8, borderRadius: 4, border: "1px solid #ddd" }}
      />
      <button style={{ marginTop: 8 }}>Send</button>
    </div>
  )
  
export default ChatOverlay