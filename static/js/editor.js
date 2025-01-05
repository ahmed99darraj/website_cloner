class ElementEditor {
    constructor(container) {
        this.container = container;
        console.log('ElementEditor initialized');
    }

    showEditor(element) {
        console.log('Showing editor for element:', element);
        
        // إنشاء مربع الحوار
        const $dialog = $('<div>').addClass('editor-dialog');
        
        // إنشاء النموذج
        const $form = $('<form>').addClass('editor-form');
        
        // إضافة الحقول حسب نوع العنصر
        if (element.tagName.toLowerCase() === 'img') {
            $form.append(`
                <div class="form-group">
                    <label>رابط الصورة:</label>
                    <input type="text" name="src" value="${$(element).attr('src') || ''}" />
                </div>
                <div class="form-group">
                    <label>النص البديل:</label>
                    <input type="text" name="alt" value="${$(element).attr('alt') || ''}" />
                </div>
                <div class="form-group">
                    <label>تحميل صورة جديدة:</label>
                    <input type="file" name="newImage" accept="image/*" />
                </div>
            `);
        } else if (element.tagName.toLowerCase() === 'a') {
            $form.append(`
                <div class="form-group">
                    <label>الرابط:</label>
                    <input type="text" name="href" value="${$(element).attr('href') || ''}" />
                </div>
                <div class="form-group">
                    <label>النص:</label>
                    <input type="text" name="text" value="${$(element).text() || ''}" />
                </div>
            `);
        } else {
            $form.append(`
                <div class="form-group">
                    <label>النص:</label>
                    <textarea name="text">${$(element).text() || ''}</textarea>
                </div>
            `);
        }
        
        // إضافة أزرار الإجراءات
        $form.append(`
            <div class="form-actions">
                <button type="submit" class="save-btn">حفظ</button>
                <button type="button" class="cancel-btn">إلغاء</button>
            </div>
        `);
        
        // إضافة معالج الحدث للنموذج
        $form.on('submit', async (e) => {
            e.preventDefault();
            console.log('Form submitted');
            
            try {
                const $form = $(e.target);
                const formData = new FormData($form[0]);
                const elementType = element.tagName.toLowerCase();
                let data = {
                    elementType,
                    originalContent: this.getOriginalContent(element)
                };
                
                // معالجة تحميل الصور
                if (elementType === 'img') {
                    const newImage = formData.get('newImage');
                    if (newImage && newImage.size > 0) {
                        console.log('Uploading new image:', newImage);
                        const imageFormData = new FormData();
                        imageFormData.append('file', newImage);
                        
                        try {
                            const uploadResponse = await fetch('/upload_image', {
                                method: 'POST',
                                body: imageFormData
                            });
                            
                            if (!uploadResponse.ok) {
                                const errorText = await uploadResponse.text();
                                console.error('Upload response not OK:', errorText);
                                throw new Error('فشل تحميل الصورة: ' + errorText);
                            }
                            
                            const uploadResult = await uploadResponse.json();
                            console.log('Upload result:', uploadResult);
                            
                            if (uploadResult.success) {
                                data.newSrc = uploadResult.file_url;
                            } else {
                                throw new Error(uploadResult.error || 'فشل تحميل الصورة');
                            }
                        } catch (uploadError) {
                            console.error('Error uploading image:', uploadError);
                            throw uploadError;
                        }
                    } else {
                        data.newSrc = formData.get('src');
                        data.newAlt = formData.get('alt');
                    }
                } else if (elementType === 'a') {
                    data.newHref = formData.get('href');
                    data.newText = formData.get('text');
                } else {
                    data.newText = formData.get('text');
                }
                
                console.log('Sending update request with data:', data);
                
                // إرسال التحديثات إلى الخادم
                const response = await fetch(`/update_element?file_id=${window.FILE_ID}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify(data)
                });
                
                if (!response.ok) {
                    throw new Error('فشل الاتصال بالخادم');
                }
                
                const result = await response.json();
                if (result.success) {
                    console.log('Element updated successfully');
                    // تحديث العنصر في الصفحة
                    this.updateElement(element, data);
                    this.closeEditor($dialog);
                } else {
                    throw new Error(result.error);
                }
            } catch (error) {
                console.error('Error updating element:', error);
                alert('حدث خطأ أثناء تحديث العنصر: ' + error.message);
            }
        });
        
        // إضافة معالج حدث للإلغاء
        $form.find('.cancel-btn').on('click', () => {
            this.closeEditor($dialog);
        });
        
        // إضافة النموذج إلى مربع الحوار
        $dialog.append($form);
        
        // إضافة مربع الحوار إلى الصفحة
        $(document.body).append($dialog);
        
        // حساب موقع العنصر بالنسبة للصفحة
        const $element = $(element);
        const $iframe = $('#previewFrame');
        const iframeOffset = $iframe.offset();
        const elementOffset = $element.offset();
        
        // تحويل الإحداثيات من داخل الـ iframe إلى الصفحة الرئيسية
        const top = iframeOffset.top + elementOffset.top;
        const left = iframeOffset.left + elementOffset.left;
        
        // الحصول على أبعاد مربع الحوار والـ iframe
        const dialogHeight = $dialog.outerHeight();
        const dialogWidth = $dialog.outerWidth();
        const iframeHeight = $iframe.height();
        const iframeWidth = $iframe.width();
        
        // التأكد من أن مربع الحوار يظهر داخل حدود الـ iframe
        let finalTop = top;
        let finalLeft = left;
        
        if (finalTop + dialogHeight > iframeOffset.top + iframeHeight) {
            finalTop = iframeOffset.top + iframeHeight - dialogHeight;
        }
        if (finalLeft + dialogWidth > iframeOffset.left + iframeWidth) {
            finalLeft = iframeOffset.left + iframeWidth - dialogWidth;
        }
        
        // تعيين الموقع النهائي
        $dialog.css({
            position: 'absolute',
            top: Math.max(iframeOffset.top, finalTop) + 'px',
            left: Math.max(iframeOffset.left, finalLeft) + 'px',
            zIndex: 1000
        });
    }

    getOriginalContent(element) {
        const $element = $(element);
        const content = {};
        
        switch (element.tagName.toLowerCase()) {
            case 'img':
                content.src = $element.attr('src');
                content.alt = $element.attr('alt');
                break;
            case 'a':
                content.href = $element.attr('href');
                content.text = $element.text();
                break;
            default:
                content.text = $element.text();
        }
        
        return content;
    }

    updateElement(element, data) {
        const $element = $(element);
        
        switch (element.tagName.toLowerCase()) {
            case 'img':
                if (data.newSrc) $element.attr('src', data.newSrc);
                if (data.newAlt) $element.attr('alt', data.newAlt);
                break;
            case 'a':
                if (data.newHref) $element.attr('href', data.newHref);
                if (data.newText) $element.text(data.newText);
                break;
            default:
                if (data.newText) $element.text(data.newText);
        }
    }

    closeEditor($dialog) {
        $dialog.remove();
    }
}
