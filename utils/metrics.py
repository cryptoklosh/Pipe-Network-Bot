from prometheus_client import Gauge, Info, Counter

pipe_info = Info("pipe", "Info about pipe-guardian node")
mined_pipe_gauge = Gauge('mined_pipe', 'Number of mined pipe points', ['account'])
pipe_requests_total_counter = Counter('pipe_requests_total', 'API mining requests', ['account', 'status'])