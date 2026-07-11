/**
 * Reusable modal component.
 */

export interface ModalOptions {
  title: string;
  content: string | HTMLElement;
  onConfirm?: (data: any) => void;
  onCancel?: () => void;
  confirmText?: string;
  cancelText?: string | null;
}

export class Modal {
  private element: HTMLElement;
  private options: ModalOptions;

  constructor(options: ModalOptions) {
    this.options = options;
    this.element = this.create();
  }

  private create(): HTMLElement {
    const modal = document.createElement('div');
    modal.className = 'modal hidden';
    
    const content = document.createElement('div');
    content.className = 'modal-content';

    const header = document.createElement('div');
    header.className = 'modal-header';
    const h3 = document.createElement('h3');
    h3.textContent = this.options.title;
    header.appendChild(h3);

    const closeBtn = document.createElement('span');
    closeBtn.className = 'close-button';
    closeBtn.innerHTML = '&times;';
    closeBtn.onclick = () => this.hide();
    header.appendChild(closeBtn);

    content.appendChild(header);

    const body = document.createElement('div');
    body.className = 'modal-body';
    if (typeof this.options.content === 'string') {
      body.innerHTML = this.options.content;
    } else {
      body.appendChild(this.options.content);
    }
    content.appendChild(body);

    const footer = document.createElement('div');
    footer.className = 'modal-footer';

    if (this.options.cancelText !== null) {
      const cancelBtn = document.createElement('button');
      cancelBtn.className = 'btn btn-secondary';
      cancelBtn.textContent = this.options.cancelText || 'Cancel';
      cancelBtn.onclick = () => {
        if (this.options.onCancel) this.options.onCancel();
        this.hide();
      };
      footer.appendChild(cancelBtn);
    }

    const confirmBtn = document.createElement('button');
    confirmBtn.className = 'btn btn-primary';
    confirmBtn.textContent = this.options.confirmText || 'Confirm';
    confirmBtn.onclick = () => {
      const data = this.getFormData();
      if (this.options.onConfirm) this.options.onConfirm(data);
      this.hide();
    };
    footer.appendChild(confirmBtn);

    content.appendChild(footer);
    modal.appendChild(content);
    document.body.appendChild(modal);

    return modal;
  }

  public show() {
    this.element.classList.remove('hidden');
  }

  public hide() {
    this.element.classList.add('hidden');
    // Remove from DOM after transition
    setTimeout(() => {
        if (this.element.parentNode) {
            document.body.removeChild(this.element);
        }
    }, 300);
  }

  private getFormData(): any {
    const inputs = this.element.querySelectorAll('input, select, textarea');
    const data: any = {};
    inputs.forEach((input: any) => {
      if (input.name) {
        if (input.type === 'checkbox') {
          data[input.name] = input.checked;
        } else if (input.type === 'number') {
          data[input.name] = parseFloat(input.value);
        } else {
          data[input.name] = input.value;
        }
      }
    });
    return data;
  }
}

/**
 * Utility for quick parameter modals.
 */
export function showParameterModal(title: string, fields: any[], onConfirm: (data: any) => void) {
  const container = document.createElement('div');
  container.className = 'form-container';

  fields.forEach(f => {
    const group = document.createElement('div');
    group.className = 'form-group';
    
    const label = document.createElement('label');
    label.textContent = f.label;
    group.appendChild(label);

    let input: HTMLInputElement | HTMLSelectElement;
    if (f.type === 'select') {
      input = document.createElement('select');
      f.options.forEach((o: any) => {
        const opt = document.createElement('option');
        opt.value = o.value;
        opt.textContent = o.label;
        input.appendChild(opt);
      });
    } else {
      input = document.createElement('input');
      input.type = f.type || 'text';
      if (f.min !== undefined) (input as HTMLInputElement).min = f.min;
      if (f.max !== undefined) (input as HTMLInputElement).max = f.max;
      if (f.step !== undefined) (input as HTMLInputElement).step = f.step;
    }
    input.name = f.name;
    input.value = f.value !== undefined ? f.value : '';
    group.appendChild(input);
    container.appendChild(group);
  });

  const modal = new Modal({
    title,
    content: container,
    onConfirm
  });
  modal.show();
}
