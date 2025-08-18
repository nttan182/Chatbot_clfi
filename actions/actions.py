from typing import Any, Text, Dict, List, Optional, Tuple
from datetime import datetime, date
from rasa_sdk import FormValidationAction, logger
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
import psycopg2
from rasa_sdk.events import SlotSet, UserUtteranceReverted

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="chatbot_clfi",
        user="postgres",
        password="2101235"
    )


class ActionFallbackReset(Action):
    def name(self) -> str:
        return "action_fallback_reset"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict):

        dispatcher.utter_message(text="Xin lỗi, tôi chưa hiểu câu hỏi. Bạn có thể nhập lại thông tin theo cách khác giúp tôi không?")

        return [
            # SlotSet("gioi_thieu_trung_tam", None),
            SlotSet("khoa_hoc", None),
            SlotSet("chi_tiet_quy_dinh", None),
            UserUtteranceReverted()  # Xóa câu người dùng vừa nhập để hội thoại không bị kẹt
        ]

class ActionCheckPostgreConnection(Action):
    def name(self):
        return "action_check_postgre_connection"

    def run(self, dispatcher: CollectingDispatcher, tracker, domain):

        try:
            # Cập nhật thông tin kết nối theo thực tế
            conn = get_db_connection()
            dispatcher.utter_message(text="Kết nối PostgreSQL thành công!")
            conn.close()

        except Exception as e:
            dispatcher.utter_message(text=f"Lỗi kết nối PostgreSQL: {str(e)}")

        return []

class ActionXemChuongTrinhDaoTao(Action):
    def name(self):
        return "action_xem_chuong_trinh_dao_tao"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict):

        try:
            # Kết nối đến PostgreSQL
            conn = get_db_connection()
            cursor = conn.cursor()

            # Truy vấn danh sách các quy định
            cursor.execute("SELECT ten_chuong_trinh FROM hoi_chuong_trinh_dao_tao ORDER BY ten_chuong_trinh ASC")
            results = cursor.fetchall()

            if results:
                message = "Danh sách các chương trình hiện có: <br>"
                for idx, row in enumerate(results, start=1):
                    message += f"&nbsp &nbsp &nbsp{idx}. {row[0]}<br>"
                message += "Bạn có thể truy cập để xem chi tiết các thông tin qua liên kết: <a href='https://trungtamnnth.ctuet.edu.vn/'> https://trungtamnnth.ctuet.edu.vn/</a>. Bạn có muốn hỏi thêm chi tiết về chương trình nào không?"
            else:
                message = "Hiện chưa có thông tin chương trình bạn đang hỏi."

        except Exception as e:
            message = f"Đã xảy ra lỗi khi kết nối CSDL: {str(e)}"
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

        dispatcher.utter_message(text=message)
        return []

class ValidateFormChuongTrinhGiangDay(FormValidationAction):
    def name(self) -> Text:
        return "validate_form_chuong_trinh_giang_day"

    def validate_khoa_hoc(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        khoa_hoc = (slot_value or "").strip()
        if khoa_hoc:
            return {"khoa_hoc": khoa_hoc}
        dispatcher.utter_message(text="Bạn vui lòng cung cấp chính xác tên khóa học nhé!")
        return {"khoa_hoc": None}
def fetch_chuong_trinh_giang_day(khoa_hoc: str) -> str | Optional[Tuple[str, str]]:

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT dt.ten_chuong_trinh, gd.noi_dung
                      FROM hoi_chuong_trinh_giang_day gd
                      JOIN hoi_chuong_trinh_dao_tao dt
                        ON dt.ma_chuong_trinh = gd.ma_chuong_trinh
                     WHERE gd.ma_chuong_trinh ILIKE %s
                    """,
                    (f"%{khoa_hoc.strip()}%",),
                )
                row = cursor.fetchone()
                if row:
                    return row[0], row[1]
    except Exception:
        logger.exception("Lỗi khi truy vấn chương trình giảng dạy")
    return row
class ActionXemChuongTrinhGiangDay(Action):
    def name(self) -> Text:
        return "action_xem_chuong_trinh_giang_day"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> List[Dict[Text, Any]]:

        khoa_hoc = tracker.get_slot("khoa_hoc")
        if not khoa_hoc:
            dispatcher.utter_message(response="utter_ask_khoa_hoc")
            return []

        result = fetch_chuong_trinh_giang_day(khoa_hoc)
        if result:
            ten, noi_dung = fetch_chuong_trinh_giang_day(khoa_hoc)
            if noi_dung:
                dispatcher.utter_message(
                        text=f"{ten}: {noi_dung}"
                    )
        else:
            dispatcher.utter_message(text="Không tìm thấy chương trình nào.")
        return [SlotSet("khoa_hoc", None)]


class ValidateFormChuongTrinhKhung(FormValidationAction):
    def name(self) -> Text:
        return "validate_form_chuong_trinh_khung"

    def validate_khoa_hoc(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        # Dùng same slot tên "khoa_hoc" để nhận input mã hoặc tên chương trình khung
        khoa_hoc = (slot_value or "").strip()
        if not khoa_hoc:
            dispatcher.utter_message(text="Bạn vui lòng cung cấp chính xác tên khóa học nhé!")
            return {"khoa_hoc": None}
        return {"khoa_hoc": khoa_hoc}
def fetch_chuong_trinh_khung(khoa_hoc: str) -> Optional[Tuple[str, str]]:
    normalized = khoa_hoc.strip()
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Thử match theo mã chương trình khung
                cursor.execute(
                    """
                    SELECT dt.ten_chuong_trinh, k.noi_dung
                      FROM hoi_chuong_trinh_khung k
                      JOIN hoi_chuong_trinh_dao_tao dt
                        ON dt.ma_chuong_trinh = k.ma_chuong_trinh
                     WHERE k.ma_chuong_trinh ILIKE %s
                    """,
                    (f"%{normalized}%",),
                )
                row = cursor.fetchone()
                if row and row[0] and row[1]:
                    return row[0], row[1]
                return row[0], "Không có thông tin."
    except Exception:
        logger.exception("[fetch_chuong_trinh_khung] Lỗi khi truy vấn chương trình khung")
    return None
class ActionXemChuongTrinhKhung(Action):
    def name(self) -> Text:
        return "action_xem_chuong_trinh_khung"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> List[Dict[Text, Any]]:
        khoa_hoc = tracker.get_slot("khoa_hoc")
        if not khoa_hoc:
            dispatcher.utter_message(response="utter_ask_khoa_hoc")
            return []

        result = fetch_chuong_trinh_khung(khoa_hoc)
        if result:
            ten, noi_dung = result
            dispatcher.utter_message(
                text=(
                    f"{ten}: {noi_dung}"
                )
            )
        else:
            dispatcher.utter_message(
                text=(
                    f"Không tìm thấy chương trình khung phù hợp. "
                    "Vui lòng kiểm tra lại mã hoặc tên."
                )
            )

        return [SlotSet("khoa_hoc", None)]

class ValidateFormThoiGianDaoTao(FormValidationAction):
    def name(self) -> Text:
        return "validate_form_thoi_gian_dao_tao"

    def validate_khoa_hoc(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        # Dùng same slot tên "khoa_hoc" để nhận input mã hoặc tên chương trình khung
        khoa_hoc = (slot_value or "").strip()
        if not khoa_hoc:
            dispatcher.utter_message(text="Bạn vui lòng cung cấp tên chương trình nhé!")
            return {"khoa_hoc": None}
        return {"khoa_hoc": khoa_hoc}

def fetch_thoi_gian_dao_tao(khoa_hoc: str) -> Optional[Tuple[str, str, str]]:
    normalized = khoa_hoc.strip()
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Thử match theo mã chương trình khung
                cursor.execute(
                    """
                    SELECT dt.ten_chuong_trinh, tg.thoi_luong, tg.thoi_gian_hoc
                      FROM thoi_gian_dao_tao tg
                      JOIN hoi_chuong_trinh_dao_tao dt
                        ON dt.ma_chuong_trinh = tg.ma_chuong_trinh
                     WHERE tg.ma_chuong_trinh ILIKE %s
                    """,
                    (f"%{normalized}%",),
                )
                row = cursor.fetchone()
                if row:
                    return row[0], row[1], row[2]
    except Exception:
        logger.exception("[fetch_thoi_gian_dao_tao] Lỗi khi truy vấn")
    return row

class ActionXemThoiLuong(Action):
    def name(self) -> Text:
        return "action_xem_thoi_luong"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> List[Dict[Text, Any]]:
        khoa_hoc = tracker.get_slot("khoa_hoc")
        if not khoa_hoc:
            dispatcher.utter_message(response="utter_ask_khoa_hoc")
            return []

        result = fetch_thoi_gian_dao_tao(khoa_hoc)
        if result:
            ten, thoi_luong, thoi_gian_hoc = result
            if not thoi_luong and not thoi_gian_hoc:
                dispatcher.utter_message(
                    text=f"{ten} hiện chưa có thông tin về thời lượng và thời gian học."
                )
            elif not thoi_luong:
                dispatcher.utter_message(
                    text=f"{ten} được đào tạo <b>{thoi_gian_hoc}</b>, nhưng chưa có thông tin về thời lượng học."
                )
            elif not thoi_gian_hoc:
                dispatcher.utter_message(
                    text=f"{ten} có tổng cộng <b>{thoi_luong} học</b>, nhưng chưa có thông tin về thời gian học."
                )
            else:
                dispatcher.utter_message(
                    text=f"{ten} được đào tạo: <b>{thoi_gian_hoc}</b>, với tổng cộng <b>{thoi_luong} học</b>."
                )
        else:
            dispatcher.utter_message(
                text=(
                    f"Chưa có thông tin về thời gian của khóa học này. Vui lòng liên hệ trực tiếp trung tâm để biết thêm chi tiết."
                )
            )

        return [SlotSet("khoa_hoc", None)]

class ValidateFormChuanDauRa(FormValidationAction):
    def name(self) -> Text:
        return "validate_form_chuan_dau_ra"

    def validate_khoa_hoc(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        # Dùng same slot tên "khoa_hoc" để nhận input mã hoặc tên chương trình khung
        khoa_hoc = (slot_value or "").strip()
        if not khoa_hoc:
            dispatcher.utter_message(text="Bạn vui lòng cung cấp mã hoặc tên chương trình khung nhé!")
            return {"khoa_hoc": None}
        return {"khoa_hoc": khoa_hoc}
def fetch_chuan_dau_ra(khoa_hoc: str) -> Optional[Tuple[str, str, str]]:
    normalized = khoa_hoc.strip()
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Thử match theo mã chương trình khung
                cursor.execute(
                    """
                    SELECT dt.ten_chuong_trinh, cdr.noi_dung
                      FROM hoi_chuan_dau_ra cdr
                      JOIN hoi_chuong_trinh_dao_tao dt
                        ON dt.ma_chuong_trinh = cdr.ma_chuong_trinh
                        WHERE cdr.ma_chuong_trinh ILIKE %s
                    """,
                    (f"%{normalized}%",),
                )
                row = cursor.fetchone()
                if row and row[0] and row[1]:
                    return row[0], row[1]
    except Exception:
        logger.exception("[fetch_chuan_dau_ra] Lỗi khi truy vấn chương trình")
    return None
class ActionTraChuanDauRa(Action):

    def name(self) -> Text:
        return "action_tra_cuu_chuan_dau_ra"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> List[Dict[Text, Any]]:
        khoa_hoc = tracker.get_slot("khoa_hoc")
        if not khoa_hoc:
            dispatcher.utter_message(response="utter_ask_khoa_hoc")
            return []

        result = fetch_chuan_dau_ra(khoa_hoc)
        if result:
            ten, noi_dung = result
            dispatcher.utter_message(
                text=(
                        f"{noi_dung}"
                    )
            )
        else:
            dispatcher.utter_message(
                text=(
                    f"Vui lòng liên hệ trực tiếp trung tâm để biết thêm chi tiết."
                )
            )

        return [SlotSet("khoa_hoc", None)]

class ValidateFormHocPhi(FormValidationAction):
    def name(self) -> Text:
        return "validate_form_hoc_phi"

    def validate_khoa_hoc(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        khoa_hoc = (slot_value or "").strip()
        if not khoa_hoc:
            dispatcher.utter_message(text="Bạn vui lòng cung cấp chính xác tên chương trình nhé!")
            return {"khoa_hoc": None}
        return {"khoa_hoc": khoa_hoc}
def fetch_hoc_phi(khoa_hoc: str) -> Optional[Tuple[str, str, Optional[str]]]:
    normalized = khoa_hoc.strip()
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT dt.ghi_chu, hp.hoc_phi, hp.ghi_chu
                      FROM hoi_hoc_phi hp
                      JOIN hoi_chuong_trinh_dao_tao dt
                        ON dt.ma_chuong_trinh = hp.ma_chuong_trinh
                     WHERE hp.ma_chuong_trinh ILIKE %s
                    """,
                    (f"%{normalized}%",),
                )
                row = cursor.fetchone()
                if row and row[0] and row[1] and row[2]:
                    return row[0], row[1], row[2]
    except Exception:
        logger.exception("[fetch_hoc_phi] Lỗi khi truy vấn học phí")
    return None
class ActionTraCuuHocPhi(Action):
    def name(self) -> Text:
        return "action_tra_cuu_hoc_phi"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> List[Dict[Text, Any]]:
        khoa_hoc = tracker.get_slot("khoa_hoc")
        if not khoa_hoc:
            dispatcher.utter_message(response="utter_ask_khoa_hoc")
            return []

        result = fetch_hoc_phi(khoa_hoc)
        if result:
            ten, hoc_phi, ghi_chu = result

            try:
                hoc_phi_fmt = f"{int(float(hoc_phi)):,}".replace(",", ".")
            except Exception:
                hoc_phi_fmt = str(hoc_phi)

            if not hoc_phi and not ghi_chu:
                dispatcher.utter_message(
                    text=f"{ten} hiện chưa có thông tin về học phí."
                )
            elif not ghi_chu:
                dispatcher.utter_message(
                    text=(
                        f"Học phí cho chương trình <b>{ten}</b> là <b>{hoc_phi_fmt} đồng</b>."
                    )
                )
            else:
                dispatcher.utter_message(
                    text=(
                        f"Học phí cho chương trình <b>{ten}</b> là <b>{hoc_phi_fmt} đồng</b> ({ghi_chu})"
                    )
                )
        else:
            dispatcher.utter_message(
                text=(
                    f"Vui lòng liên hệ trực tiếp trung tâm để biết thêm chi tiết về học phí."
                )
            )

        return [SlotSet("khoa_hoc", None)]

class ValidateFormPhiThiLai(FormValidationAction):
    def name(self) -> Text:
        return "validate_form_phi_thi_lai"

    def validate_khoa_hoc(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        khoa_hoc = (slot_value or "").strip()
        if not khoa_hoc:
            dispatcher.utter_message(text="Bạn vui lòng cung cấp chính xác tên khóa học nhé!")
            return {"khoa_hoc": None}
        return {"khoa_hoc": khoa_hoc}
def fetch_phi_thi_lai(khoa_hoc: str) -> Optional[Tuple[str, str]]:
    normalized = khoa_hoc.strip()
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT dt.ghi_chu, pt.phi_thi_lai
                      FROM hoi_phi_thi_lai pt
                      JOIN hoi_chuong_trinh_dao_tao dt
                        ON dt.ma_chuong_trinh = pt.ma_chuong_trinh
                     WHERE pt.ma_chuong_trinh ILIKE %s
                    """,
                    (f"%{normalized}%",),
                )
                row = cursor.fetchone()
                if row and row[0] and row[1]:
                    return row[0], row[1]
    except Exception:
        logger.exception("[fetch_phi_thi_lai] Lỗi khi truy vấn phí thi lại")
    return None
class ActionTraCuuPhiThiLai(Action):
    def name(self) -> Text:
        return "action_tra_cuu_phi_thi_lai"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> List[Dict[Text, Any]]:
        khoa_hoc = tracker.get_slot("khoa_hoc")
        if not khoa_hoc:
            dispatcher.utter_message(response="utter_ask_khoa_hoc")
            return []

        result = fetch_phi_thi_lai(khoa_hoc)
        if result:
            ten, phi_thi_lai = result

            try:
                phi_fmt = f"{int(float(phi_thi_lai)):,}".replace(",", ".")
            except Exception:
                phi_fmt = str(phi_thi_lai)

            if ten and phi_thi_lai:
                dispatcher.utter_message(
                    text=(
                        f"Phí thi lại cho chương trình <b>{ten}</b> là <b>{phi_fmt} đồng/lần thi</b>."
                    )
                )
            else:
                dispatcher.utter_message(
                    text=f"Chưa có quy định đối với {ten}."
                )
        else:
            dispatcher.utter_message(
                text=(
                    f"Vui lòng liên hệ trực tiếp trung tâm để biết thêm chi tiết về phí thi lại."
                )
            )

        return [SlotSet("khoa_hoc", None)]

class validate_form_dieu_kien_bao_luu(FormValidationAction):
    def name(self) -> Text:
        return "validate_form_dieu_kien_bao_luu"

    def validate_khoa_hoc(self, slot_value: Any, dispatcher: CollectingDispatcher,
                          tracker: Tracker, domain: Dict) -> Dict[Text, Any]:
        # Kiểm tra nếu khóa học hợp lệ (giả định có hàm kiểm tra DB)
        if slot_value:
            return {"khoa_hoc": slot_value}
        dispatcher.utter_message(text="Bạn vui lòng cung cấp chính xác tên khóa học nhé!")
        return {"khoa_hoc": None}
class ActionTraCuuDieuKienBaoLuu(Action):
    def name(self) -> Text:
        return "action_tra_cuu_dieu_kien_bao_luu"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[
        Dict[Text, Any]]:
        khoa_hoc = tracker.get_slot("khoa_hoc")

        if not khoa_hoc:
            dispatcher.utter_message(text="Tôi chưa nhận được thông tin về khóa học bạn muốn hỏi.")
            return []

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT mo_ta 
                FROM hoi_dieu_kien_bao_luu 
                WHERE ma_chuong_trinh ILIKE %s
            """, (f"%{khoa_hoc}%",))

            result = cursor.fetchone()

            if result and result[0]:
                #dispatcher.utter_message(text=f"{khoa_hoc}: {result[0]}")
                dispatcher.utter_message(text=f"{result[0]}")
                return [SlotSet("khoa_hoc", None)]
            else:
                dispatcher.utter_message(
                    text=f"Hiện tại chưa có thông tin cho khóa học {khoa_hoc}.")
                return [SlotSet("khoa_hoc", None)]
        except Exception as e:
            dispatcher.utter_message(text=f"Đã xảy ra lỗi khi truy vấn CSDL: {e}")

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

        return []

class ActionXemDanhSachQuyDinh(Action):
    def name(self):
        return "action_xem_danh_sach_quy_dinh"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict):

        try:
            # Kết nối đến PostgreSQL
            conn = get_db_connection()
            cursor = conn.cursor()

            # Truy vấn danh sách các quy định
            cursor.execute("SELECT ten_qui_dinh FROM danh_sach_quy_dinh ORDER BY ten_qui_dinh ASC")
            results = cursor.fetchall()

            if results:
                message = "Danh sách các quy định, quy chế và các văn bản hiện có: <br>"
                for idx, row in enumerate(results, start=1):
                    message += f"&nbsp &nbsp &nbsp{idx}. {row[0]}<br>"
                message += "Bạn có thể truy cập để xem chi tiết các thông tin qua liên kết: <a href='https://phongctct.ctuet.edu.vn/sinh-vien/'> https://phongctct.ctuet.edu.vn/sinh-vien</a>. Bạn có muốn hỏi thêm chi tiết về Quy định, Quy chế hay văn bản nào không?"
            else:
                message = "Hiện chưa có thông tin quy định bạn đang hỏi."

        except Exception as e:
            message = f"Đã xảy ra lỗi khi kết nối CSDL: {str(e)}"
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

        dispatcher.utter_message(text=message)
        return []
class ActionXemQuyDinhChiTiet(Action):
    def name(self) -> Text:
        return "action_tra_cuu_thong_tin_chi_tiet_quy_dinh"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[
        Dict[Text, Any]]:
        chi_tiet_quy_dinh = tracker.get_slot("chi_tiet_quy_dinh")

        if not chi_tiet_quy_dinh:
            dispatcher.utter_message(text="Tôi chưa nhận được thông tin về quy định bạn muốn hỏi.")
            return []

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT mo_ta
                FROM danh_sach_quy_dinh
                WHERE ten_qui_dinh ILIKE %s
            """, (f"%{chi_tiet_quy_dinh}%",))

            result = cursor.fetchone()

            if result and result[0]:
                #dispatcher.utter_message(text=f"{khoa_hoc}: {result[0]}")
                dispatcher.utter_message(text=f"{result[0]}")
                # return [SlotSet("danh_sach_quy_dinh", None)]
            else:
                dispatcher.utter_message(
                    text=f"Hiện tại chưa có thông tin cho quy định bạn đang hỏi.")
                # return [SlotSet("danh_sach_quy_dinh", None)]
        except Exception as e:
            dispatcher.utter_message(text=f"Đã xảy ra lỗi khi truy vấn CSDL: {e}")

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

        return [SlotSet("chi_tiet_quy_dinh", None)]

class ValidateFormDieuKienDuThi(FormValidationAction):
    def name(self) -> Text:
        return "validate_form_dieu_kien_du_thi"

    def validate_khoa_hoc(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        khoa_hoc = (slot_value or "").strip()
        if not khoa_hoc:
            dispatcher.utter_message(text="Bạn vui lòng cung cấp chính xác tên khóa học nhé!")
            return {"khoa_hoc": None}
        return {"khoa_hoc": khoa_hoc}
def fetch_dieu_kien_du_thi(khoa_hoc: str) -> Optional[str]:
    normalized = khoa_hoc.strip()
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT mo_ta
                      FROM hoi_dieu_kien_du_thi
                     WHERE ma_chuong_trinh ILIKE %s
                    """,
                    (f"%{normalized}%",),
                )
                row = cursor.fetchone()
                if row and row[0]:
                    return row[0]
    except Exception:
        logger.exception("[fetch_dieu_kien_du_thi] Lỗi khi truy vấn điều kiện dự thi")
    return None
class ActionTraCuuDieuKienDuThi(Action):
    def name(self) -> Text:
        return "action_tra_cuu_dieu_kien_du_thi"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> List[Dict[Text, Any]]:
        khoa_hoc = tracker.get_slot("khoa_hoc")
        if not khoa_hoc:
            dispatcher.utter_message(response="utter_ask_khoa_hoc")
            return []

        result = fetch_dieu_kien_du_thi(khoa_hoc)
        if result:
            dispatcher.utter_message(text=result)
        else:
            dispatcher.utter_message(
                text=(
                    f"Vui lòng liên hệ trực tiếp trung tâm để biết thêm chi tiết về điều kiện dự thi."
                )
            )

        return [SlotSet("khoa_hoc", None)]

class ValidateTraCuuLichDaoTao(FormValidationAction):
    def name(self) -> Text:
        return "validate_form_tra_cuu_lich_dao_tao"

    def validate_khoa_hoc(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        khoa_hoc = (slot_value or "").strip()
        if not khoa_hoc:
            dispatcher.utter_message(text="Bạn vui lòng cung cấp chính xác tên khóa học nhé!")
            return {"khoa_hoc": None}
        return {"khoa_hoc": khoa_hoc}
def fetch_lich_dao_tao(khoa_hoc: str) -> Optional[Dict[str, Any]]:

    normalized = (khoa_hoc or "").strip()
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT dt.ghi_chu,
                           ld.khoa_dao_tao,
                           ld.ngay_khai_giang,
                           ld.ngay_thi
                      FROM hoi_lich_dao_tao ld
                      JOIN hoi_chuong_trinh_dao_tao dt
                        ON dt.ma_chuong_trinh = ld.ma_chuong_trinh
                     WHERE ld.ma_chuong_trinh ILIKE %s
                        OR dt.ten_chuong_trinh ILIKE %s
                        OR ld.ma_khoa_hoc ILIKE %s
                     ORDER BY ld.ngay_khai_giang NULLS LAST,
                              ld.ngay_thi       NULLS LAST,
                              ld.id ASC
                     LIMIT 20;
                    """,
                    (f"%{normalized}%", f"%{normalized}%", f"%{normalized}%"),
                )
                rows = cursor.fetchall()
                if not rows:
                    return None

                ten = rows[0][0] or normalized
                items = []
                for r in rows:
                    items.append({
                        "khoa": r[1],
                        "kg": r[2],
                        "thi": r[3],
                    })
                return {"ten": ten, "items": items}
    except Exception:
        logger.exception("[fetch_lich_dao_tao] Lỗi khi truy vấn lịch đào tạo")
    return None
class ActionTraCuuLichDaoTao(Action):
    def name(self) -> Text:
        return "action_tra_cuu_lich_dao_tao"

    def _fmt_date(self, d: Optional[datetime.date]) -> str:
        if not d:
            return "—"
        try:
            return d.strftime("%d/%m/%Y")
        except Exception:
            return str(d)

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> List[Dict[Text, Any]]:

        khoa_hoc = tracker.get_slot("khoa_hoc")
        if not khoa_hoc:
            dispatcher.utter_message(response="utter_ask_khoa_hoc")
            return []

        data = fetch_lich_dao_tao(khoa_hoc)
        if not data:
            # Không có bản ghi nào khớp hoàn toàn → thông điệp chung
            dispatcher.utter_message(
                text="Mình chưa tìm thấy lịch đào tạo phù hợp với từ khóa bạn cung cấp. Bạn vui lòng kiểm tra lại tên/mã khóa học hoặc liên hệ Trung tâm để được hỗ trợ nhé."
            )
            return [SlotSet("khoa_hoc", None)]

        ten = data["ten"]
        items = data["items"]

        all_null = all(
            (it["khoa"] is None) and (it["kg"] is None) and (it["thi"] is None)
            for it in items
        )

        if all_null:
            year = datetime.now().year
            dispatcher.utter_message(
                text=(
                    f"Thông tin lịch khai giảng các lớp <b>{ten}</b> trong năm <b>{year}</b> chưa có, do đó bạn nên liên hệ chi tiết thông tin mở lớp qua số điện thoại của Trung tâm hoặc Facebook để tìm hiểu thông tin chính xác hơn."
                )
            )
            return [SlotSet("khoa_hoc", None)]

        valid = [
            it for it in items
            if (it["khoa"] is not None) and (it["kg"] is not None) and (it["thi"] is not None)
        ]

        if not valid:
            semi = [
                it for it in items
                if (it["kg"] is not None) or (it["thi"] is not None) or (it["khoa"] is not None)
            ][:5]
            if semi:
                lines = []
                for it in semi:
                    khoa_show = it["khoa"] or it["ma_khoa"] or "(Chưa đặt tên khóa)"
                    kg = self._fmt_date(it["kg"])
                    thi = self._fmt_date(it["thi"])
                    lines.append(f"• <b>{khoa_show}</b>: Khai giảng {kg}, Thi {thi}")
                dispatcher.utter_message(
                    text=f"<b>Lịch {ten} (tối đa 5 khóa):</b><br>" + "<br>".join(lines)
                )
            else:
                year = datetime.now().year
                dispatcher.utter_message(
                    text=(
                        f"Thông tin lịch khai giảng các lớp <b>{ten}</b> trong năm <b>{year}</b> chưa có. "
                        f"Bạn vui lòng liên hệ Trung tâm để biết thêm chi tiết nhé."
                    )
                )
            return [SlotSet("khoa_hoc", None)]

        # Lấy tối đa 5 bản ghi đầy đủ
        valid = valid[:5]
        lines = []
        for it in valid:
            khoa_show = it["khoa"] or it["ma_khoa"] or "(Chưa đặt tên khóa)"
            kg = self._fmt_date(it["kg"])
            thi = self._fmt_date(it["thi"])
            lines.append(f"• <b>{khoa_show}</b>: Khai giảng {kg}, Thi {thi}")

        dispatcher.utter_message(
            text=f"<b>Lịch {ten} (tối đa 5 khóa):</b><br>" + "<br>".join(lines)
        )

        return [SlotSet("khoa_hoc", None)]