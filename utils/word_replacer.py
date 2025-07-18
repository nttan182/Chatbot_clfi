import re


def load_replacement_data(filename):
    """
    Hàm đọc dữ liệu thay thế từ file

    Args:
        filename (str): Tên file chứa dữ liệu thay thế

    Returns:
        dict: Dictionary chứa các từ cần thay thế và từ thay thế
    """
    replacements = {}
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if ':' in line:
                    parts = line.split(':', 1)
                    target_word = parts[0].strip()
                    words_to_replace = [word.strip() for word in parts[1].split(',')]
                    for word in words_to_replace:
                        if word:  # Chỉ thêm từ không rỗng
                            replacements[word] = target_word
    except FileNotFoundError:
        print(f"Không tìm thấy file {filename}")
        return {}
    except Exception as e:
        print(f"Lỗi khi đọc file {filename}: {e}")
        return {}

    return replacements


def replace_words(text, replacements):
    """
    Hàm thay thế các từ trong văn bản

    Args:
        text (str): Văn bản cần thay thế
        replacements (dict): Dictionary chứa các từ cần thay thế

    Returns:
        str: Văn bản đã được thay thế
    """
    # Tạo một bản sao của văn bản để xử lý
    replaced_text = text

    # Sắp xếp các từ theo độ dài giảm dần để tránh trường hợp
    # từ ngắn hơn được thay thế trước từ dài hơn
    sorted_words = sorted(replacements.keys(), key=len, reverse=True)

    for word in sorted_words:
        # Sử dụng regex để tìm và thay thế từ
        # \b đảm bảo chỉ thay thế từ hoàn chỉnh, không phải một phần của từ khác
        pattern = r'\b' + re.escape(word) + r'\b'
        replaced_text = re.sub(pattern, replacements[word], replaced_text, flags=re.IGNORECASE)

    return replaced_text
