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

def load_stopwords(filename):
    """
    Hàm đọc danh sách stopword từ file

    Args:
        filename (str): Tên file chứa danh sách stopword

    Returns:
        set: Tập hợp các stopword
    """
    stopwords = set()
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            for line in file:
                word = line.strip()
                if word:
                    stopwords.add(word.lower())  # Chuyển về chữ thường để so sánh
    except FileNotFoundError:
        print(f"Không tìm thấy file {filename}")
    except Exception as e:
        print(f"Lỗi khi đọc file {filename}: {e}")

    return stopwords

def replace_words(text, replacements, stopwords=None):
    """
    Hàm thay thế và lọc stopword trong văn bản

    Args:
        text (str): Văn bản cần thay thế
        replacements (dict): Dictionary chứa các từ cần thay thế
        stopwords (set): Tập hợp các stopword cần loại bỏ

    Returns:
        str: Văn bản đã được thay thế
    """
    # Loại bỏ ký tự không phải chữ cái, số hoặc khoảng trắng
    text = re.sub(r'[^\w\s]', ' ', text, flags=re.UNICODE)
    replaced_text = text

    # Thay thế từ theo dictionary
    sorted_words = sorted(replacements.keys(), key=len, reverse=True)

    for word in sorted_words:
        # Sử dụng regex để tìm và thay thế từ
        # \b đảm bảo chỉ thay thế từ hoàn chỉnh, không phải một phần của từ khác
        pattern = r'\b' + re.escape(word) + r'\b'
        replaced_text = re.sub(pattern, replacements[word], replaced_text, flags=re.IGNORECASE)

    # Tách từ để xử lý stopword
    words = replaced_text.split()
    if stopwords:
        words = [word for word in words if word.lower() not in stopwords]

    return ' '.join(words)
