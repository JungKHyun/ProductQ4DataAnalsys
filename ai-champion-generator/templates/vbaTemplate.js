/**
 * vbaTemplate.js
 * 문제 3 — Excel VBA 코드 생성
 */

export function vbaTemplate(profile) {
  const { recommendedMetric: metric, recommendedGroup: group, columns, rowCount } = profile;
  const today = new Date().toLocaleDateString('ko-KR');

  return `'==========================================================
' 모듈명: DataAnalysisReport
' 설명: ${group}별 ${metric} 자동 분석 보고서 생성 VBA 코드
' 생성일: ${today}
' 생성도구: AI챔피언 데이터분석 문제 자동 생성기
'==========================================================
Option Explicit

' ── 설정 상수 (필요 시 수정) ──────────────────────────────
Const CSV_FILE_PATH As String = "C:\\데이터\\data.csv"  ' ← 실제 CSV 파일 경로로 변경
Const SHEET_RAW    As String = "원본데이터"
Const SHEET_REPORT As String = "분석결과"
Const GROUP_COL    As String = "${group}"     ' 그룹 기준 컬럼명
Const METRIC_COL   As String = "${metric}"    ' 집계 지표 컬럼명

'==========================================================
' 메인 프로시저: 보고서 전체 생성
'==========================================================
Public Sub CreateAnalysisReport()
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual

    On Error GoTo ErrorHandler

    ' 1단계: CSV 원본 데이터 불러오기
    Call ImportCSVData

    ' 2단계: 분석결과 시트 생성
    Call CreateReportSheet

    ' 3단계: 집계표 생성
    Call BuildSummaryTable

    ' 4단계: 차트 생성
    Call CreateBarChart

    ' 완료 메시지
    MsgBox "분석 보고서가 완성되었습니다!" & vbCrLf & _
           "· 원본데이터 시트: CSV 원본 데이터" & vbCrLf & _
           "· 분석결과 시트: 집계표 및 차트", _
           vbInformation, "AI챔피언 데이터분석"

    Application.ScreenUpdating = True
    Application.Calculation = xlCalculationAutomatic
    Exit Sub

ErrorHandler:
    Application.ScreenUpdating = True
    Application.Calculation = xlCalculationAutomatic
    MsgBox "오류 발생: " & Err.Description & vbCrLf & _
           "CSV 파일 경로를 확인하거나 시트 이름 충돌을 점검하세요.", _
           vbCritical, "오류"
End Sub

'==========================================================
' 프로시저: CSV 데이터를 원본데이터 시트에 불러오기
'==========================================================
Private Sub ImportCSVData()
    Dim ws      As Worksheet
    Dim filePath As String

    ' 기존 원본데이터 시트 삭제 후 재생성
    Call SafeDeleteSheet(SHEET_RAW)
    Set ws = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.Count))
    ws.Name = SHEET_RAW

    filePath = CSV_FILE_PATH

    ' QueryTable을 이용한 CSV 가져오기
    With ws.QueryTables.Add( _
        Connection:="TEXT;" & filePath, _
        Destination:=ws.Range("A1"))
        .TextFileParseType    = xlDelimited
        .TextFileCommaDelimiter = True
        .TextFileColumnDataTypes = Array(${columns.map(() => 1).join(', ')})
        .TextFileStartRow     = 1
        .RefreshStyle         = xlInsertDeleteCells
        .Refresh BackgroundQuery:=False
        .Delete  ' QueryTable 연결 삭제 (데이터는 유지)
    End With

    ' 헤더 굵게 표시
    ws.Rows(1).Font.Bold = True
    ws.Rows(1).Interior.Color = RGB(30, 64, 175)
    ws.Rows(1).Font.Color = RGB(255, 255, 255)
    ws.Columns.AutoFit

    ' 보고서 제목 삽입 (행 앞에 삽입)
    ws.Rows(1).Insert Shift:=xlDown
    ws.Range("A1").Value = "[ ${group} 기준 ${metric} 분석 원본 데이터 ]"
    ws.Range("A1").Font.Bold = True
    ws.Range("A1").Font.Size = 14
    ws.Range("A1").Font.Color = RGB(30, 64, 175)
End Sub

'==========================================================
' 프로시저: 분석결과 시트 생성 및 기본 구조 설정
'==========================================================
Private Sub CreateReportSheet()
    Dim ws As Worksheet

    ' 기존 분석결과 시트 삭제 후 재생성
    Call SafeDeleteSheet(SHEET_REPORT)
    Set ws = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(SHEET_RAW))
    ws.Name = SHEET_REPORT

    ' ── 보고서 헤더 ──
    With ws
        .Range("A1").Value = "데이터 분석 보고서"
        .Range("A1").Font.Bold = True
        .Range("A1").Font.Size = 18
        .Range("A1").Font.Color = RGB(30, 64, 175)

        .Range("A2").Value = "분석 기준: " & GROUP_COL & " × " & METRIC_COL
        .Range("A2").Font.Color = RGB(100, 116, 139)

        .Range("A3").Value = "작성일: " & Format(Now(), "YYYY년 MM월 DD일")
        .Range("A3").Font.Color = RGB(100, 116, 139)

        .Range("A4").Value = "생성도구: AI챔피언 데이터분석 문제 자동 생성기"
        .Range("A4").Font.Color = RGB(100, 116, 139)

        .Range("A1:D4").Interior.Color = RGB(239, 246, 255)
        .Rows(5).RowHeight = 8
    End With
End Sub

'==========================================================
' 프로시저: 그룹별 집계표 생성
'==========================================================
Private Sub BuildSummaryTable()
    Dim wsRaw    As Worksheet
    Dim wsReport As Worksheet
    Dim lastRow  As Long
    Dim groupCol As Long
    Dim metricCol As Long
    Dim dict     As Object
    Dim cell     As Range
    Dim i        As Long
    Dim reportRow As Long

    Set wsRaw    = ThisWorkbook.Sheets(SHEET_RAW)
    Set wsReport = ThisWorkbook.Sheets(SHEET_REPORT)

    ' 원본 데이터 마지막 행 확인 (헤더가 2행에 있으므로 +1)
    lastRow = wsRaw.Cells(wsRaw.Rows.Count, 1).End(xlUp).Row

    ' 컬럼 번호 찾기
    groupCol  = FindColumnIndex(wsRaw, GROUP_COL, 2)
    metricCol = FindColumnIndex(wsRaw, METRIC_COL, 2)

    If groupCol = 0 Then
        MsgBox "컬럼을 찾을 수 없습니다: " & GROUP_COL, vbExclamation: Exit Sub
    End If
    If metricCol = 0 Then
        MsgBox "컬럼을 찾을 수 없습니다: " & METRIC_COL, vbExclamation: Exit Sub
    End If

    ' 딕셔너리로 그룹별 합계 계산
    Set dict = CreateObject("Scripting.Dictionary")
    For i = 3 To lastRow  ' 3행부터 (1행: 제목, 2행: 헤더)
        Dim gKey As String
        Dim mVal As Double
        gKey = CStr(wsRaw.Cells(i, groupCol).Value)
        mVal = Val(wsRaw.Cells(i, metricCol).Value)
        If dict.Exists(gKey) Then
            dict(gKey) = dict(gKey) + mVal
        Else
            dict.Add gKey, mVal
        End If
    Next i

    ' 분석결과 시트에 집계표 작성
    reportRow = 6
    With wsReport
        ' 집계표 제목
        .Cells(reportRow, 1).Value = "${group}별 ${metric} 집계표"
        .Cells(reportRow, 1).Font.Bold = True
        .Cells(reportRow, 1).Font.Size = 12
        .Cells(reportRow, 1).Font.Color = RGB(30, 64, 175)
        reportRow = reportRow + 1

        ' 헤더
        .Cells(reportRow, 1).Value = GROUP_COL
        .Cells(reportRow, 2).Value = METRIC_COL & " 합계"
        .Cells(reportRow, 3).Value = "비율(%)"
        .Rows(reportRow).Font.Bold = True
        .Rows(reportRow).Interior.Color = RGB(30, 64, 175)
        .Rows(reportRow).Font.Color = RGB(255, 255, 255)
        reportRow = reportRow + 1

        ' 전체 합계 계산
        Dim totalSum As Double
        totalSum = 0
        Dim k As Variant
        For Each k In dict.Keys
            totalSum = totalSum + dict(k)
        Next k

        ' 데이터 행 작성 (내림차순 정렬)
        Dim keys() As Variant, vals() As Variant
        keys = dict.Keys
        vals = dict.Items
        ' 간단 버블정렬
        Dim swapped As Boolean
        Dim tmpK As Variant, tmpV As Variant
        Do
            swapped = False
            For i = 0 To UBound(vals) - 1
                If vals(i) < vals(i + 1) Then
                    tmpK = keys(i): keys(i) = keys(i + 1): keys(i + 1) = tmpK
                    tmpV = vals(i): vals(i) = vals(i + 1): vals(i + 1) = tmpV
                    swapped = True
                End If
            Next i
        Loop While swapped

        For i = 0 To UBound(keys)
            .Cells(reportRow, 1).Value = keys(i)
            .Cells(reportRow, 2).Value = vals(i)
            .Cells(reportRow, 2).NumberFormat = "#,##0"
            If totalSum > 0 Then
                .Cells(reportRow, 3).Value = Round((vals(i) / totalSum) * 100, 1)
                .Cells(reportRow, 3).NumberFormat = "0.0%"
                .Cells(reportRow, 3).Value = vals(i) / totalSum
            End If
            If i Mod 2 = 0 Then .Rows(reportRow).Interior.Color = RGB(248, 250, 252)
            reportRow = reportRow + 1
        Next i

        ' 합계 행
        .Cells(reportRow, 1).Value = "합계"
        .Cells(reportRow, 2).Value = totalSum
        .Cells(reportRow, 2).NumberFormat = "#,##0"
        .Cells(reportRow, 3).Value = 1
        .Cells(reportRow, 3).NumberFormat = "0.0%"
        .Rows(reportRow).Font.Bold = True
        .Rows(reportRow).Interior.Color = RGB(219, 234, 254)

        .Columns("A:C").AutoFit
    End With
End Sub

'==========================================================
' 프로시저: 막대 차트 생성
'==========================================================
Private Sub CreateBarChart()
    Dim wsReport As Worksheet
    Dim chartObj As ChartObject
    Dim cht       As Chart
    Dim dataRange As Range
    Dim lastRow   As Long

    Set wsReport = ThisWorkbook.Sheets(SHEET_REPORT)
    lastRow = wsReport.Cells(wsReport.Rows.Count, 1).End(xlUp).Row - 1  ' 합계행 제외

    ' 데이터 범위 (헤더 포함, 합계 제외)
    Set dataRange = wsReport.Range("A8:B" & lastRow)

    ' 차트 삽입
    Set chartObj = wsReport.ChartObjects.Add( _
        Left:=wsReport.Range("E6").Left, _
        Top:=wsReport.Range("E6").Top, _
        Width:=480, Height:=320)

    Set cht = chartObj.Chart
    cht.SetSourceData Source:=dataRange
    cht.ChartType = xlColumnClustered

    ' 차트 서식
    With cht
        .HasTitle = True
        .ChartTitle.Text = "${group}별 ${metric} 현황"
        .ChartTitle.Font.Bold = True
        .ChartTitle.Font.Color = RGB(30, 64, 175)
        .ChartTitle.Font.Size = 12

        ' 색상 설정
        Dim ser As Series
        Set ser = .SeriesCollection(1)
        ser.Interior.Color = RGB(59, 130, 246)
        ser.Name = METRIC_COL

        ' 데이터 레이블 표시
        ser.HasDataLabels = True
        ser.DataLabels.NumberFormat = "#,##0"
        ser.DataLabels.Font.Size = 8

        ' 축 서식
        .Axes(xlCategory).TickLabels.Font.Size = 9
        .Axes(xlValue).TickLabels.NumberFormat = "#,##0"
        .PlotArea.Interior.Color = RGB(248, 250, 252)
        .ChartArea.Interior.Color = RGB(255, 255, 255)
    End With
End Sub

'==========================================================
' 유틸: 시트 안전 삭제
'==========================================================
Private Sub SafeDeleteSheet(sheetName As String)
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets(sheetName)
    On Error GoTo 0
    If Not ws Is Nothing Then
        Application.DisplayAlerts = False
        ws.Delete
        Application.DisplayAlerts = True
    End If
End Sub

'==========================================================
' 유틸: 헤더 행에서 컬럼 인덱스 찾기
'==========================================================
Private Function FindColumnIndex(ws As Worksheet, colName As String, headerRow As Long) As Long
    Dim i As Long
    Dim lastCol As Long
    lastCol = ws.Cells(headerRow, ws.Columns.Count).End(xlToLeft).Column
    For i = 1 To lastCol
        If Trim(ws.Cells(headerRow, i).Value) = colName Then
            FindColumnIndex = i
            Exit Function
        End If
    Next i
    FindColumnIndex = 0
End Function
`;
}
