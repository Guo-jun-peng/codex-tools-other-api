interface Props {
  data: any
}

export default function StatusBar({ data }: Props) {
  const running = data?.running
  return (
    <div className="status-bar">
      <span>
        <span className={`status-dot ${running ? 'online' : 'offline'}`} />
        {running ? '代理运行中' : '代理未连接'}
      </span>
      {running && (
        <>
          <span>{data.host}:{data.port}</span>
          <span>请求: {data.stats?.request_count ?? 0}</span>
        </>
      )}
    </div>
  )
}
