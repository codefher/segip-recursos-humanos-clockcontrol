#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests para el modulo de attendance
"""
import json
from datetime import date, datetime, timedelta

import pytest

from clockcontrol.core.attendance import AttendanceProcessor, AttendanceMark


class MockAttendance:
    """Mock de objeto de asistencia ZK"""
    def __init__(self, user_id: str, timestamp: str):
        self.user_id = user_id
        self.timestamp = timestamp
    
    def __str__(self) -> str:
        return f"Attendance {self.user_id} : {self.timestamp} 0"


class TestAttendanceMark:
    """Tests para la clase AttendanceMark"""
    
    def test_creation(self):
        """Test de creacion de AttendanceMark"""
        mark = AttendanceMark(
            carnet="12345",
            date_mark="2026-02-07",
            time_mark="08:00:00",
            ip_clock="192.168.1.100",
            id_reloj_bio=42,
        )
        
        assert mark.carnet == "12345"
        assert mark.date_mark == "2026-02-07"
        assert mark.time_mark == "08:00:00"
        assert mark.ip_clock == "192.168.1.100"
        assert mark.id_reloj_bio == 42
    
    def test_to_db_dict(self):
        """Test de conversion a diccionario para DB"""
        mark = AttendanceMark(
            carnet="12345",
            date_mark="2026-02-07",
            time_mark="08:00:00",
            ip_clock="192.168.1.100",
            id_reloj_bio=42,
        )
        
        db_dict = mark.to_db_dict()
        
        assert db_dict["incarnet"] == "12345"
        assert db_dict["indate_mark"] == "2026-02-07"
        assert db_dict["intime_mark"] == "08:00:00"
        assert db_dict["inip_clock"] == "192.168.1.100"
        assert db_dict["inid_reloj_bio"] == 42


class TestAttendanceProcessor:
    """Tests para AttendanceProcessor"""
    
    def setup_method(self):
        """Setup para cada test"""
        self.processor = AttendanceProcessor(days_back=1)
        self.ip_clock = "192.168.1.100"
        self.clock_id = 42
    
    def test_process_empty_list(self):
        """Test con lista vacia"""
        result = self.processor.process([], self.ip_clock, self.clock_id)
        assert result == []
    
    def test_process_none_values(self):
        """Test con valores None en la lista"""
        result = self.processor.process([None, None], self.ip_clock, self.clock_id)
        assert result == []
    
    def test_process_filters_old_dates(self):
        """Test que filtra marcajes antiguos"""
        today = date.today()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)
        
        attendances = [
            MockAttendance("12345", f"{today} 08:00:00"),
            MockAttendance("67890", f"{yesterday} 17:30:00"),
            MockAttendance("11111", f"{two_days_ago} 09:00:00"),  # Debe ser filtrado
        ]
        
        result = self.processor.process(attendances, self.ip_clock, self.clock_id)
        
        # Solo deben pasar hoy y ayer
        assert len(result) == 2
        carnets = [m.carnet for m in result]
        assert "12345" in carnets
        assert "67890" in carnets
        assert "11111" not in carnets
    
    def test_process_includes_today_and_yesterday(self):
        """Test que incluye hoy y ayer"""
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        attendances = [
            MockAttendance("12345", f"{today} 08:00:00"),
            MockAttendance("67890", f"{yesterday} 17:30:00"),
        ]
        
        result = self.processor.process(attendances, self.ip_clock, self.clock_id)
        
        assert len(result) == 2
    
    def test_process_sets_correct_ip(self):
        """Test que asigna IP correcta"""
        today = date.today()
        attendances = [MockAttendance("12345", f"{today} 08:00:00")]
        
        result = self.processor.process(attendances, self.ip_clock, self.clock_id)
        
        assert result[0].ip_clock == self.ip_clock
    
    def test_process_sets_correct_clock_id(self):
        """Test que asigna ID de reloj correcto"""
        today = date.today()
        attendances = [MockAttendance("12345", f"{today} 08:00:00")]
        
        result = self.processor.process(attendances, self.ip_clock, self.clock_id)
        
        assert result[0].id_reloj_bio == self.clock_id
    
    def test_to_json_returns_valid_json(self):
        """Test que to_json retorna JSON valido"""
        marks = [
            AttendanceMark(
                carnet="12345",
                date_mark="2026-02-07",
                time_mark="08:00:00",
                ip_clock="192.168.1.100",
                id_reloj_bio=42,
            )
        ]
        
        json_str = AttendanceProcessor.to_json(marks)
        
        # Debe ser JSON valido
        data = json.loads(json_str)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["incarnet"] == "12345"
    
    def test_to_json_empty_list(self):
        """Test to_json con lista vacia"""
        json_str = AttendanceProcessor.to_json([])
        data = json.loads(json_str)
        assert data == []
    
    def test_days_back_parameter(self):
        """Test del parametro days_back"""
        processor = AttendanceProcessor(days_back=3)
        today = date.today()
        three_days_ago = today - timedelta(days=3)
        four_days_ago = today - timedelta(days=4)
        
        attendances = [
            MockAttendance("12345", f"{three_days_ago} 08:00:00"),
            MockAttendance("67890", f"{four_days_ago} 08:00:00"),  # Debe ser filtrado
        ]
        
        result = processor.process(attendances, self.ip_clock, self.clock_id)
        
        assert len(result) == 1
        assert result[0].carnet == "12345"


class TestAttendanceProcessorEdgeCases:
    """Tests para casos borde"""
    
    def test_malformed_attendance_string(self):
        """Test con string de attendance malformado"""
        processor = AttendanceProcessor()
        
        class BadAttendance:
            def __str__(self):
                return "malformed string"
        
        result = processor.process([BadAttendance()], "192.168.1.1", 1)
        assert result == []
    
    def test_invalid_date_format(self):
        """Test con formato de fecha invalido"""
        processor = AttendanceProcessor()
        
        class BadDateAttendance:
            def __str__(self):
                return "Attendance 12345 : not-a-date 08:00:00 0"
        
        result = processor.process([BadDateAttendance()], "192.168.1.1", 1)
        assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
