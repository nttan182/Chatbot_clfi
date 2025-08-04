from typing import Any, Text, Dict, List, Optional, Tuple
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
        if not khoa_hoc:
            dispatcher.utter_message(text="Bạn vui lòng cung cấp chính xác tên khóa học nhé!")
            return {"khoa_hoc": None}
        # Nếu cần, thêm kiểm tra tồn tại trong DB ở đây rồi normalize tên
        return {"khoa_hoc": khoa_hoc}

def fetch_chuong_trinh_giang_day(khoa_hoc: str) -> str | None:

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
                if row and row[0]:
                    return row[0]
    except Exception:
        logger.exception("Lỗi khi truy vấn chương trình giảng dạy")
    return None

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

        noi_dung = fetch_chuong_trinh_giang_day(khoa_hoc)
        if noi_dung:
            dispatcher.utter_message(
                text=f"Thông tin chương trình giảng dạy: {noi_dung}"
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
            dispatcher.utter_message(text="Bạn vui lòng cung cấp mã hoặc tên chương trình khung nhé!")
            return {"khoa_hoc": None}
        return {"khoa_hoc": khoa_hoc}


def fetch_chuong_trinh_khung(khoa_hoc: str) -> Optional[Tuple[str, str, str]]:
    normalized = khoa_hoc.strip()
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Thử match theo mã chương trình khung
                cursor.execute(
                    """
                    SELECT n.ma_chuong_trinh, n.ten_chuong_trinh, h.noi_dung
                      FROM hoi_chuong_trinh_khung h
                      JOIN noi_chuong_trinh_dao_tao n
                        ON n.ma_chuong_trinh = h.ma_chuong_trinh
                     WHERE h.ma_chuong_trinh ILIKE %s
                    """,
                    (f"%{normalized}%",),
                )
                row = cursor.fetchone()
                if row and row[0] and row[2]:
                    return row[0], row[1], row[2]
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
            ma, ten, noi_dung = result
            dispatcher.utter_message(
                text=(
                    f"Thông tin chương trình khung **{ten}**: {noi_dung}"
                )
            )
        else:
            dispatcher.utter_message(
                text=(
                    f"Không tìm thấy chương trình khung phù hợp với “{khoa_hoc}”. "
                    "Vui lòng kiểm tra lại mã hoặc tên."
                )
            )

        return [SlotSet("khoa_hoc", None)]

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
            cursor.execute("SELECT ten_quy_dinh FROM danh_sach_quy_dinh ORDER BY ten_quy_dinh ASC")
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
                FROM danh_sach_qui_dinh 
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

        return []

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