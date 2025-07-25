from typing import Any, Text, Dict, List
from rasa_sdk import FormValidationAction
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
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

            cursor.execute("SELECT ten_chuong_trinh FROM chuong_trinh_dao_tao;")
            records = cursor.fetchall()

            if records:
                message = "Trung tâm hiện có các chương trình giảng dạy:<br>"
                for row in records:
                    message += f"- {row[0]}<br>"
            else:
                message = "Hiện trung tâm chưa có chương trình giảng dạy nào."

            dispatcher.utter_message(text=message)

        except (Exception, psycopg2.Error) as error:
            dispatcher.utter_message(text="Đã xảy ra lỗi khi kết nối CSDL.")
            print("Lỗi kết nối CSDL:", error)

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

        return []

class ActionXemChuongTrinh(Action):
    def name(self) -> Text:
        return "action_xem_chuong_trinh_giang_day"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        # Lấy slot khoa_hoc (vd: "toeic ctut")
        khoa_hoc = tracker.get_slot("khoa_hoc")

        # Nếu user chỉ nói chung chung, chưa có slot -> hỏi lại
        if not khoa_hoc:
            dispatcher.utter_message(response="utter_ask_khoa_hoc")
            return []

        # Nếu đã có slot, thực hiện truy vấn
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT chuong_trinh_giang_day
                  FROM chuong_trinh_dao_tao
                 WHERE ma_chuong_trinh ILIKE %s
                """,
                (khoa_hoc.strip(),)
            )
            row = cursor.fetchone()

            if row and row[0]:
                ten = row[0]
                dispatcher.utter_message(text=(
                    f"Thông tin chương trình giảng dạy:\n"
                    f"- Tên chương trình: **{ten}**"
                ))
            else:
                dispatcher.utter_message(text=(
                    f"Không tìm thấy chương trình nào."
                ))

        except Exception as e:
            logger.error(f"[ActionXemChuongTrinh] Lỗi khi truy vấn DB: {e}")
            dispatcher.utter_message(text=(
                "Đã xảy ra lỗi khi kết nối cơ sở dữ liệu. "
                "Vui lòng thử lại sau."
            ))
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

        # Reset slot để lần sau user có thể tra tiếp
        return [SlotSet("khoa_hoc", None)]

class ActionXemChuongTrinhKhung(Action):
    def name(self) -> Text:
        return "action_xem_chuong_trinh_khung"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        # Lấy slot ma_ct_khung (mã chương trình khung)
        ma_ct = tracker.get_slot("ma_ct_khung")

        if not ma_ct:
            # Nếu user chưa cho mã, hỏi lại
            dispatcher.utter_message(response="utter_ask_ma_ct_khung")
            return []

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT ten_chuong_trinh
                  FROM chuong_trinh
                 WHERE ma_chuong_trinh = %s
                """,
                (ma_ct.strip(),)
            )
            row = cursor.fetchone()

            if row and row[0]:
                ten = row[0]
                dispatcher.utter_message(text=(
                    f"Chương trình khung* bạn yêu cầu:\n"
                    f" • Mã: **{ma_ct.upper()}**\n"
                    f" • Tên: **{ten}**"
                ))
            else:
                dispatcher.utter_message(text=(
                    f"Không tìm thấy chương trình khung với mã “{ma_ct}”. "
                    "Vui lòng kiểm tra lại."
                ))

        except Exception as e:
            logger.error(f"[ActionXemChuongTrinhKhung] Lỗi DB: {e}")
            dispatcher.utter_message(text=(
                "Có lỗi khi truy xuất cơ sở dữ liệu. "
                "Bạn vui lòng thử lại sau."
            ))
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

        # Reset slot để lần sau có thể tra mã khác
        return [SlotSet("ma_ct_khung", None)]

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
                FROM danh_sach_quy_dinh 
                WHERE ten_quy_dinh ILIKE %s
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
                SELECT dieu_kien_bao_luu 
                FROM thong_tin_chuong_trinh 
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
