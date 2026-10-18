"""Page-facing aggregation contracts, using temporary databases only."""
from fastapi.testclient import TestClient
from backend.main import create_app


def test_analytics_preserves_historical_dates_severity_zone_and_ack_on_restart(tmp_path):
    path = tmp_path / 'analytics.sqlite3'
    original_times = ['2023-10-08T23:30:00-02:00', '2023-10-09T03:00:00+00:00',
                      '2023-10-16T03:00:00+00:00', '2023-10-16T04:00:00+00:00']
    with TestClient(create_app(path)) as client:
        events = []
        for index, severity in enumerate(['critical', 'high', 'medium', 'low']):
            zone = client.post('/api/zones', json={'name': f'Zone {index}', 'camera_id': f'camera-{index}',
                'polygon': [[.1,.1],[.9,.1],[.9,.9],[.1,.9]], 'severity': severity}).json()
            response = client.post('/api/ingest/detections', json={'timestamp': original_times[index],
                'camera_id': f'camera-{index}', 'frame_width': 640, 'frame_height': 480,
                'detections': [{'track_id': str(index), 'class_name': 'person', 'confidence': .9,
                                'bbox': [.2,.2,.4,.8]}]})
            assert response.status_code == 200
            events.extend(response.json()['incidents'])
        assert len(events) == 4
        client.patch(f"/api/incidents/{events[0]['id']}/acknowledge", json={'acknowledged': True})
        summary = client.get('/api/analytics/summary').json()
        assert summary == {'total_incidents': 4, 'acknowledged': 1,
            'by_severity': {'critical': 1, 'high': 1, 'medium': 1, 'low': 1},
            'by_zone': {f'Zone {i}': 1 for i in range(4)},
            'trend': [{'date': '2023-10-09', 'count': 2}, {'date': '2023-10-16', 'count': 2}]}
        persisted = client.get('/api/incidents').json()
    with TestClient(create_app(path)) as client:
        assert client.get('/api/analytics/summary').json() == summary
        assert client.get('/api/incidents').json() == persisted


def test_analytics_empty_database_has_no_invented_points(tmp_path):
    with TestClient(create_app(tmp_path / 'empty.sqlite3')) as client:
        assert client.get('/api/analytics/summary').json() == {
            'total_incidents': 0, 'acknowledged': 0, 'by_severity': {}, 'by_zone': {}, 'trend': []}
