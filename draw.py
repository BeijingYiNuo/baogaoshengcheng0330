
def draw():
    import numpy as np
    import matplotlib.pyplot as plt
    from io import BytesIO
    try:
    #<REPLACE_START> 
        labels = ["A", "B", "C", "D", "E"]
        values = [65, 80, 55, 90, 75]

        plt.rcParams["font.sans-serif"] = ["SimHei"]
        plt.rcParams["axes.unicode_minus"] = False
        angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
        values = np.concatenate((values, [values[0]]))
        angles = np.concatenate((angles, [angles[0]]))
        fig, ax = plt.subplots(subplot_kw={"polar": True})
        ax.set_ylim(0, 100)
        ax.plot(angles, values, label="得分")
        ax.fill(angles, values, alpha=0.25)
        pass_score = 70
        pass_line = [pass_score] * len(angles)
        ax.plot(angles, pass_line, color="orange", linewidth=2, label="及格（70）")
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels)
        ax.legend(loc="upper right")
    #<REPLACE_END>
    except:
        pass
    img_stream = BytesIO()
    plt.savefig(img_stream, dpi=300, bbox_inches="tight")
    plt.close()
    img_stream.seek(0)
    return img_stream